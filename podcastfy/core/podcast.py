from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable, Tuple, Union, Sequence, cast
from tempfile import TemporaryDirectory
import atexit
from pydub import AudioSegment
from functools import wraps
from contextlib import contextmanager

from podcastfy.aiengines.llm.base import LLMBackend
from podcastfy.aiengines.tts.base import SyncTTSBackend, AsyncTTSBackend, TTSBackend
from podcastfy.core.audio import PodcastsAudioSegment, AudioManager
from podcastfy.core.character import Character
from podcastfy.core.content import Content
from podcastfy.core.transcript import TranscriptSegment, Transcript
from podcastfy.core.tts_configs import TTSConfig


class PodcastState(Enum):
    """Enum representing the different states of a podcast during creation."""
    INITIALIZED = 0  # Initial state when the Podcast object is created
    TRANSCRIPT_BUILT = 1  # State after the transcript has been generated
    AUDIO_SEGMENTS_BUILT = 2  # State after individual audio segments have been created
    STITCHED = 3  # Final state after all audio segments have been combined


def podcast_stage(func):
    """Decorator to manage podcast stage transitions."""

    @wraps(func)
    def probably_same_func(method, func):
        return method.__func__.__name__ == func.__name__

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        current_method = self._next_stage_methods[self.state]
        print(f"Current state: {self.state.name}")
        print(f"Executing: {func.__name__}")
        if not probably_same_func(current_method, func) and not self._reworking:
            print(f"Cannot execute {func.__name__} in current state {self.state.name}. Skipping.")
            raise Exception(f"Cannot execute {func.__name__} in current state {self.state.name}")

        try:
            result = func(self, *args, **kwargs)
            next_state = PodcastState(self.state.value + 1)
            self.state = next_state or self.state
            print(f"Done!")
            return result
        except Exception as e:
            print(f"Error in {func.__name__}: {str(e)}")
            raise

    return wrapper


class Podcast:
    """Main class for podcast creation and management."""

    def __init__(self, content: List[Content], llm_backend: LLMBackend,
                 audio_manager: AudioManager,
                 characters: Optional[List[Character]] = None):
        """
        Initialize a new Podcast instance.

        Args:
            content (str): The raw content to be processed into a podcast.
            llm_backend (LLMBackend): The language model backend for generating the transcript.
            tts_backends (List[TTSBackend]): List of available TTS backends.
            audio_temp_dir (Optional[str]): Path to a temporary directory for audio files. If None, a temporary
                directory will be created.
            characters (List[Character]): List of characters participating in the podcast.
            default_tts_n_jobs (int, optional): The default number of concurrent jobs for TTS processing.
                Defaults to 1.

        Raises:
            ValueError: If a character's preferred TTS backend is not available.
        """
        self.content = content
        self.llm_backend = llm_backend
        self.characters: Dict[str, Character] = {char.name: char for char in (characters or [Character("Host", "Podcast host", {}), Character("Guest", "Expert guest", {})])}
        self.state = PodcastState.INITIALIZED
        self._reworking = False
        self.audio_manager = audio_manager

        # Initialize attributes with null values
        self.transcript: Optional[Transcript] = None
        self.audio_segments: List[PodcastsAudioSegment] = []
        self.audio: Optional[AudioSegment] = None

        # Define the sequence of methods to be called for each stage
        self._next_stage_methods: Dict[PodcastState, Callable[[], None]] = {
            PodcastState.INITIALIZED: self.build_transcript,
            PodcastState.TRANSCRIPT_BUILT: self.build_audio_segments,
            PodcastState.AUDIO_SEGMENTS_BUILT: self.stitch_audio_segments,
        }

    def __del__(self) -> None:
        if hasattr(self, '_temp_dir'):
            self._temp_dir.cleanup()

    @classmethod
    def from_transcript(cls, transcript: Union[Sequence[Tuple[str, str]], Transcript],
                        audio_manager: AudioManager,
                        characters: List[Character]) -> 'Podcast':
        """
        Create a Podcast instance from a pre-existing transcript.

        Args:
            transcript (Union[Sequence[Tuple[str, str]], Transcript]): Pre-existing transcript.
            audio_manager (AudioManager): The audio manager instance for creating audio segments.
            characters (List[Character]): List of characters participating in the podcast.
        Returns:
            Podcast: A new Podcast instance with the transcript built and ready for audio generation.
        """
        if isinstance(transcript, Transcript):
            podcast = cls("", cast(LLMBackend, None), audio_manager=audio_manager, characters=characters)
            podcast.transcript = transcript
        else:
            raise ValueError("Transcript must be a Transcript instance")  # unimplemented
        podcast.state = PodcastState.TRANSCRIPT_BUILT
        return podcast

    def reset_to_state(self, state: PodcastState) -> None:
        """Reset the podcast to a specific state. """
        self.state = state
        self.transcript = None if state.value < PodcastState.TRANSCRIPT_BUILT.value else self.transcript
        self.audio_segments = [] if state.value < PodcastState.AUDIO_SEGMENTS_BUILT.value else self.audio_segments
        self.audio = None if state.value < PodcastState.STITCHED.value else self.audio

    @contextmanager
    def rework(self, target_state: PodcastState, auto_finalize: bool = True):
        """Context manager for reworking the podcast from a specific state."""
        original_state = self.state
        self._reworking = True

        if target_state == PodcastState.INITIALIZED and self.llm_backend is None:
            raise ValueError("Cannot rewind to INITIALIZED state without an LLM backend.")
        
        if target_state.value < PodcastState.TRANSCRIPT_BUILT.value and self.llm_backend is None:
            raise ValueError("Cannot rewind past TRANSCRIPT_BUILT state without an LLM backend.")

        if target_state.value < self.state.value:
            print(f"Rewinding from {self.state.name} to {target_state.name}")
            self.reset_to_state(target_state)

        try:
            yield
        finally:
            self._reworking = False
            if self.state.value < original_state.value:
                print(
                    f"Warning: Podcast is now in an earlier state ({self.state.name}) than before reworking ({original_state.name}). You may want to call finalize() to rebuild.")
                if auto_finalize:
                    self.finalize()

    @podcast_stage
    def build_transcript(self) -> None:
        """Build the podcast transcript using the LLM backend."""
        generated_segments = self.llm_backend.generate_transcript(self.content, list(self.characters.values()))

        segments = []
        for segment in generated_segments:
            if isinstance(segment, tuple) and len(segment) == 2:
                speaker, text = segment
                if speaker.name in self.characters:
                    tts_config = cast(Dict[str, Any], self.characters[speaker.name].tts_configs.get(self.characters[speaker.name].preferred_tts, {}))
                    segments.append(TranscriptSegment(text, self.characters[speaker.name], tts_config))
            else:
                print(f"Invalid segment: {segment}")
                continue
            # If the segment doesn't match the expected format, we'll skip it

        self.transcript = Transcript(segments, {"source": "Generated content"})

    @podcast_stage
    def build_audio_segments(self) -> None:
        """Build audio segments from the transcript."""
        if self.transcript is not None:
            self.audio_segments = self.audio_manager.create_audio_segments(self.transcript)
        else:
            print("Error: Transcript is None")
            raise ValueError("Transcript must be built before creating audio segments")

    @podcast_stage
    def stitch_audio_segments(self) -> None:
        """Stitch all audio segments together to form the final podcast audio."""
        # order segments by filename
        segments_to_stitch = sorted(self.audio_segments, key=lambda segment: segment.filepath)

        self.audio = sum((segment.audio for segment in segments_to_stitch), AudioSegment.empty())

    def _build_next_stage(self) -> bool:
        """Build the next stage of the podcast."""
        print("state: ", self.state)
        if self.state == PodcastState.STITCHED:
            return False

        next_method = self._next_stage_methods[self.state]
        next_method()
        return True

    def finalize(self) -> None:
        """Finalize the podcast by building all remaining stages."""
        while self._build_next_stage():
            pass

    def save(self, filepath: str) -> None:
        """Save the finalized podcast audio to a file."""
        if self.state != PodcastState.STITCHED:
            raise ValueError("Podcast can only be saved after audio is stitched")

        if self.audio:
            self.audio.export(filepath, format="mp3")
        else:
            raise ValueError("No stitched audio to save")

    def export_transcript(self, filepath: str, format_: str = "plaintext") -> None:
        """Save the podcast transcript to a file."""
        if self.state.value < PodcastState.TRANSCRIPT_BUILT.value:
            raise ValueError("Transcript can only be saved after it is built")

        if self.transcript:
            self.transcript.export(filepath, format_)
        else:
            raise ValueError("No transcript to save")

    def dump_transcript(self, filepath: str) -> None:
        """Dump the podcast transcript to a JSON file."""
        if self.state.value < PodcastState.TRANSCRIPT_BUILT.value:
            raise ValueError("Transcript can only be dumped after it is built")

        if self.transcript:
            self.transcript.dump(filepath)
        else:
            raise ValueError("No transcript to dump")

    @classmethod
    def load_transcript(cls, filepath: str, tts_backends: List[Union[SyncTTSBackend, AsyncTTSBackend]],
                        characters: List[Character]) -> 'Podcast':
        """Load a podcast from a transcript JSON file."""
        character_dict = {char.name: char for char in characters}
        transcript = Transcript.load(filepath, character_dict)
        return cls.from_transcript(transcript, tts_backends, characters)


# Usage example: Step-by-step podcast creation
if __name__ == "__main__":
    from tempfile import NamedTemporaryFile


    class DummyLLMBackend(LLMBackend):
        def generate_text(self, prompt: str, characters: List[Character]) -> List[Tuple[Character, str]]:
            return [(characters[0], "Welcome to our podcast!"), (characters[1], "Thanks for having me!")]


    class DummyTTSBackend(SyncTTSBackend):
        def __init__(self, name: str):
            self.name = name

        def text_to_speech(self, text: str, character: Character, output_path: Path) -> Path:
            audio = AudioSegment.silent(duration=1000)
            audio.export(str(output_path), format="mp3")
            return output_path


    # Define TTS backends
    openai_tts = DummyTTSBackend("openai")
    elevenlabs_tts = DummyTTSBackend("elevenlabs")

    # Define TTS backends
    host = Character(
        name="Host",
        role="Podcast host",
        tts_configs={
            "openai": TTSConfig(voice="en-US-Neural2-F", backend="openai", extra_args={"speaking_rate": 1.0}),
            "elevenlabs": TTSConfig(voice="Rachel", backend="elevenlabs", extra_args={"stability": 0.5})
        },
        default_description_for_llm="{name} is an enthusiastic podcast host. Speaks clearly and engagingly."
    )

    guest = Character(
        name="Guest",
        role="Expert guest",
        tts_configs={
            "openai": TTSConfig(voice="en-US-Neural2-D", backend="openai", extra_args={"pitch": -2.0}),
            "elevenlabs": TTSConfig(voice="Antoni", backend="elevenlabs", extra_args={"stability": 0.8})
        },
        default_description_for_llm="{name} is an expert guest. Shares knowledge in a friendly manner."
    )

    # Initialize the podcast
    podcast = Podcast(
        content="""
        This is a sample content for our podcast.
        It includes information from multiple sources that have already been parsed.
        """,
        llm_backend=DummyLLMBackend(),
        tts_backends=[openai_tts, elevenlabs_tts],
        characters=[host, guest],
    )
    print(f"Initial state: {podcast.state}")

    # Step 1: Build transcript
    podcast.build_transcript()
    print(f"After building transcript: {podcast.state}")
    print(f"Transcript: {podcast.transcript}")

    # Step 2: Build audio segments
    podcast.build_audio_segments()
    print(f"After building audio segments: {podcast.state}")
    print(f"Number of audio segments: {len(podcast.audio_segments)}")

    # Step 3: Stitch audio segments
    podcast.stitch_audio_segments()
    print(f"After stitching audio: {podcast.state}")

    # Rework example: modify the transcript and rebuild (auto_finalize is True by default)
    with podcast.rework(PodcastState.TRANSCRIPT_BUILT):
        print(f"Inside rework context, state: {podcast.state}")
        podcast.transcript.segments.append(
            TranscriptSegment("This is a new segment", podcast.characters["Host"]))
        print("Added new segment to transcript")

        # Rebuild audio segments and stitch
        podcast.build_audio_segments()

    print(f"After rework: {podcast.state}")

    # Add a new audio segment (auto_finalize is True by default)
    with NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
        AudioSegment.silent(duration=500).export(temp_file.name, format="mp3")

    with podcast.rework(PodcastState.AUDIO_SEGMENTS_BUILT):
        new_segment = PodcastsAudioSegment(Path(temp_file.name), 500,
                                           TranscriptSegment("New audio segment", podcast.characters["Host"]))
        podcast.audio_segments.insert(0, new_segment)

    # Save the final podcast
    podcast.save("./final.mp3")
    podcast.export_transcript("./final.txt", format_="plaintext")
    print("Saved podcast and transcript")

    # Example with pre-existing transcript using from_transcript class method
    pre_existing_transcript = [
        ("Host", "Welcome to our podcast created from a pre-existing transcript!"),
        ("Guest", "Thank you for having me. I'm excited to be here.")
    ]

    podcast_from_transcript = Podcast.from_transcript(
        transcript=pre_existing_transcript,
        tts_backends=[openai_tts, elevenlabs_tts],
        characters=[host, guest]
    )

    print(f"Podcast created from transcript initial state: {podcast_from_transcript.state}")
    print(f"Transcript: {podcast_from_transcript.transcript}")

    # Finalize the podcast (this will skip transcript generation and move directly to audio generation)
    podcast_from_transcript.finalize()
    podcast_from_transcript.save("./from_transcript.mp3")
    print("Saved podcast created from transcript")
