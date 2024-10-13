import logging
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable, Tuple, Union, Sequence, Type, NamedTuple
from pydub import AudioSegment as PydubAudioSegment
from functools import wraps
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager

from podcastfy.character import Character, TTSConfig

class PodcastState(Enum):
    """Enum representing the different states of a podcast during creation."""
    INITIALIZED = 0  # Initial state when the Podcast object is created
    TRANSCRIPT_BUILT = 1  # State after the transcript has been generated
    AUDIO_SEGMENTS_BUILT = 2  # State after individual audio segments have been created
    STITCHED = 3  # Final state after all audio segments have been combined


class LLMBackend(ABC):
    """Abstract base class for Language Model backends."""

    @abstractmethod
    def generate_text(self, prompt: str, characters: List['Character']) -> List[Tuple[Character, str]]:
        """
        Generate text based on a given prompt.

        Args:
            prompt (str): The input prompt for text generation.

        Returns:
            List[Tuple[str, str]]: A list of tuples containing speaker and text.
        """
        pass


class SyncTTSBackend(ABC):
    """Protocol for synchronous Text-to-Speech backends."""

    name: str

    @abstractmethod
    def text_to_speech(self, text: str, character: 'Character') -> Path:
        """
        Convert text to speech synchronously.

        Args:
            text (str): The text to convert to speech.
            character (Character): The character for which to generate speech.

        Returns:
            Path: Path to the generated audio file.
        """
        pass


class AsyncTTSBackend(ABC):
    """Protocol for asynchronous Text-to-Speech backends."""

    name: str

    @abstractmethod
    async def async_text_to_speech(self, text: str, character: 'Character') -> Path:
        """
        Convert text to speech asynchronously.

        Args:
            text (str): The text to convert to speech.
            character (Character): The character for which to generate speech.

        Returns:
            Path: Path to the generated audio file.
        """
        pass


class TranscriptSegment:
    """Represents a segment of the podcast transcript."""

    def __init__(self, text: str, speaker: Character, tts_args: Optional[Dict[str, Any]] = None):
        self.text = text
        self.speaker = speaker
        self.tts_args = tts_args or {}


class Transcript:
    """Represents the full transcript of a podcast."""

    def __init__(self, segments: List[TranscriptSegment], metadata: Dict[str, Any]):
        self.segments = segments
        self.metadata = metadata

    def save(self, filepath: str, format: str = "plaintext"):
        """Save the transcript to a file."""
        with open(filepath, 'w') as f:
            f.write(str(self))

    def __str__(self) -> str:
        """Convert the transcript to a string representation."""
        lines = []
        for segment in self.segments:
            lines.append(f"{segment.speaker.name}: {segment.text}")

        metadata_str = "\n".join([f"{key}: {value}" for key, value in self.metadata.items()])

        return f"Metadata:\n{metadata_str}\n\nTranscript:\n" + "\n".join(lines)


class AudioSegment:
    """Represents an audio segment of the podcast."""

    def __init__(self, filepath: Path, length_ms: int, transcript_segment: Optional[TranscriptSegment] = None):
        self.filepath = filepath
        self.length_ms = length_ms
        self.transcript_segment = transcript_segment
        self._audio: Optional[PydubAudioSegment] = None

    @property
    def audio(self) -> PydubAudioSegment:
        """Lazy-load the audio segment."""
        if self._audio is None:
            self._audio = PydubAudioSegment.from_file(self.filepath)
            if len(self._audio) != self.length_ms:
                raise ValueError(
                    f"Audio file length ({len(self._audio)}ms) does not match specified length ({self.length_ms}ms)")
        return self._audio


class AudioManager:
    def __init__(self, tts_backends: Dict[str, Union[SyncTTSBackend, AsyncTTSBackend]], n_jobs: int = 1):
        self.tts_backends = tts_backends
        self.n_jobs = n_jobs
        self.audio_segments = []
        self.final_audio = None

    async def _async_build_audio_segments(self, transcript: Transcript) -> List[AudioSegment]:
        async def process_segment(segment: TranscriptSegment):
            tts_backend = self.tts_backends[segment.speaker.preferred_tts]
            audio_file = await tts_backend.async_text_to_speech(segment.text, segment.speaker)
            return AudioSegment(audio_file, len(PydubAudioSegment.from_file(audio_file)), segment)

        semaphore = asyncio.Semaphore(self.n_jobs)

        async def bounded_process_segment(segment):
            async with semaphore:
                return await process_segment(segment)

        tasks = [asyncio.create_task(bounded_process_segment(segment)) for segment in transcript.segments]
        return await asyncio.gather(*tasks)

    def _sync_build_audio_segments(self, transcript: Transcript) -> List[AudioSegment]:
        def process_segment(segment: TranscriptSegment):
            tts_backend = self.tts_backends[segment.speaker.preferred_tts]
            audio_file = tts_backend.text_to_speech(segment.text, segment.speaker)
            return AudioSegment(audio_file, len(PydubAudioSegment.from_file(audio_file)), segment)

        with ThreadPoolExecutor(max_workers=self.n_jobs) as executor:
            return list(executor.map(process_segment, transcript.segments))

    def create_audio_segments(self, transcript: Transcript) -> List[AudioSegment]:
        if any(isinstance(backend, AsyncTTSBackend) for backend in self.tts_backends.values()):
            return asyncio.run(self._async_build_audio_segments(transcript))
        else:
            return self._sync_build_audio_segments(transcript)

    def stitch_audio_segments(self):
        self.final_audio = sum([segment.audio for segment in self.audio_segments])


def podcast_stage(func):
    """Decorator to manage podcast stage transitions."""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        current_method = self._next_stage_methods[self.state]
        if current_method != func and not self._reworking:
            print(f"Cannot execute {func.__name__} in current state {self.state.name}. Skipping.")
            return

        try:
            result = func(self, *args, **kwargs)
            next_state = next((state for state, method in self._next_stage_methods.items() if method == func), None)
            self.state = next_state or self.state
            return result
        except Exception as e:
            print(f"Error in {func.__name__}: {str(e)}")
            raise

    return wrapper


class Podcast:
    """Main class for podcast creation and management."""

    def __init__(self, content: str, llm_backend: LLMBackend,
                 tts_backends: List[Union[SyncTTSBackend, AsyncTTSBackend]],
                 characters: List[Character], default_tts_n_jobs: int = 1):
        """
        Initialize a new Podcast instance.

        Args:
            content (str): The raw content to be processed into a podcast.
            llm_backend (LLMBackend): The language model backend for generating the transcript.
            tts_backends (Dict[str, Union[SyncTTSBackend, AsyncTTSBackend]]): Dictionary of available TTS backends.
            characters (List[Character]): List of characters participating in the podcast.
            default_tts_n_jobs (int, optional): The default number of concurrent jobs for TTS processing.
                Defaults to 1.

        Raises:
            ValueError: If a character's preferred TTS backend is not available.
        """
        self.content = content
        self.llm_backend = llm_backend
        self.tts_backends = {backend.name: backend for backend in tts_backends}
        self.characters = {char.name: char for char in characters}
        self.default_tts_n_jobs = default_tts_n_jobs
        self.state = PodcastState.INITIALIZED
        self._reworking = False
        self.audio_manager = AudioManager(self.tts_backends, self.default_tts_n_jobs)

        # Initialize attributes with null values
        self.transcript = None
        self.audio_segments = []
        self.audio = None

        # Define the sequence of methods to be called for each stage
        self._next_stage_methods: Dict[PodcastState, Callable[[], None]] = {
            PodcastState.INITIALIZED: self.build_transcript,
            PodcastState.TRANSCRIPT_BUILT: self.build_audio_segments,
            PodcastState.AUDIO_SEGMENTS_BUILT: self.stitch_audio_segments,
        }

    @classmethod
    def from_transcript(cls, transcript: Union[Sequence[Tuple[str, str]], Transcript],
                        tts_backends: List[Union[SyncTTSBackend, AsyncTTSBackend]], characters: List[Character],
                        default_tts_n_jobs: int = 1) -> 'Podcast':
        """
        Create a Podcast instance from a pre-existing transcript.

        Args:
            transcript (Union[Sequence[Tuple[str, str]], Transcript]): Pre-existing transcript.
            tts_backends (Dict[str, Union[SyncTTSBackend, AsyncTTSBackend]]): Dictionary of available TTS backends.
            characters (List[Character]): List of characters participating in the podcast.
            default_tts_n_jobs (int, optional): The default number of concurrent jobs for TTS processing.
                Defaults to 1.

        Returns:
            Podcast: A new Podcast instance with the transcript built and ready for audio generation.
        """
        podcast = cls("", None, list(tts_backends.values()), characters, default_tts_n_jobs=default_tts_n_jobs)
        if isinstance(transcript, Transcript):
            podcast.transcript = transcript
        else:
            raise ValueError("Transcript must be a Transcript instance")  # unimplemented
        podcast.state = PodcastState.TRANSCRIPT_BUILT
        return podcast

    def reset_to_state(self, state: PodcastState):
        """Reset the podcast to a specific state."""
        self.state = state
        self.transcript = None if state.value < PodcastState.TRANSCRIPT_BUILT.value else self.transcript
        self.audio_segments = [] if state.value < PodcastState.AUDIO_SEGMENTS_BUILT.value else self.audio_segments
        self.audio = None if state.value < PodcastState.STITCHED.value else self.audio

    @contextmanager
    def rework(self, target_state: PodcastState, auto_finalize: bool = True):
        """Context manager for reworking the podcast from a specific state."""
        original_state = self.state
        self._reworking = True

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
        character_prompts = "\n\n".join([char.to_prompt() for char in self.characters.values()])
        full_prompt = f"{self.content}\n\nCharacters:\n{character_prompts}"
        generated_segments = self.llm_backend.generate_text(full_prompt, list(self.characters.values()))

        segments = [TranscriptSegment(text, speaker, self.characters[speaker])
                    for speaker, text in generated_segments if speaker in self.characters]

        self.transcript = Transcript(segments, {"source": "Generated content"})

    @podcast_stage
    def build_audio_segments(self, n_jobs: Optional[int] = None) -> None:
        """Build audio segments from the transcript."""
        self.audio_segments = self.audio_manager.create_audio_segments(self.transcript)

    @podcast_stage
    def stitch_audio_segments(self) -> None:
        """Stitch all audio segments together to form the final podcast audio."""
        self.audio = sum([segment.audio for segment in self.audio_segments])

    def _build_next_stage(self) -> bool:
        """Build the next stage of the podcast."""
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

    def save_transcript(self, filepath: str, format: str = "plaintext") -> None:
        """Save the podcast transcript to a file."""
        if self.state < PodcastState.TRANSCRIPT_BUILT:
            raise ValueError("Transcript can only be saved after it is built")

        if self.transcript:
            self.transcript.save(filepath, format)
        else:
            raise ValueError("No transcript to save")


# Usage example: Step-by-step podcast creation
if __name__ == "__main__":
    from tempfile import NamedTemporaryFile


    class DummyLLMBackend(LLMBackend):
        def generate_text(self, prompt: str, characters: List[Character]) -> List[Tuple[str, str]]:
            return [("Host", "Welcome to our podcast!"), ("Guest", "Thanks for having me!")]


    class DummyTTSBackend(SyncTTSBackend):
        def __init__(self, name: str):
            self.name = name

        def text_to_speech(self, text: str, character: Character) -> Path:
            with NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                PydubAudioSegment.silent(duration=1000).export(temp_file.name, format="mp3")
            return Path(temp_file.name)


    # Define TTS backends
    openai_tts = DummyTTSBackend("openai")
    elevenlabs_tts = DummyTTSBackend("elevenlabs")

    # Define TTS backends

    # Define characters
    host = Character(
        name="Host",
        role="Podcast host",
        tts_configs={
            "openai": {"voice": "en-US-Neural2-F", "backend": "openai", "extra_args": {"speaking_rate": 1.0}},
            "elevenlabs": {"voice": "Rachel", "backend": "elevenlabs", "extra_args": {"stability": 0.5}}
        },
        default_description_for_llm="{name} is an enthusiastic podcast host. Speaks clearly and engagingly."
    )
    guest = Character(
        name="Guest",
        role="Expert guest",
        tts_configs={"openai": {"voice": "en-US-Neural2-D", "backend": "openai", "extra_args": {"pitch": -2.0}},
                     "elevenlabs": {"voice": "Antoni", "backend": "elevenlabs", "extra_args": {"stability": 0.8}}},
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
            TranscriptSegment("This is a new segment", "Host", podcast.characters["Host"]))
        print("Added new segment to transcript")

        # Rebuild audio segments and stitch
        podcast.build_audio_segments()

    print(f"After rework: {podcast.state}")

    # Add a new audio segment (auto_finalize is True by default)
    with NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
        PydubAudioSegment.silent(duration=500).export(temp_file.name, format="mp3")

    with podcast.rework(PodcastState.AUDIO_SEGMENTS_BUILT):
        new_segment = AudioSegment(Path(temp_file.name), 500,
                                   TranscriptSegment("New audio segment", "Host", podcast.characters["Host"]))
        podcast.audio_segments.insert(0, new_segment)

    # Save the final podcast
    podcast.save("./final.mp3")
    podcast.save_transcript("./final.txt", format="plaintext")
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
