from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable
from pydub import AudioSegment as PydubAudioSegment
from functools import wraps
from contextlib import contextmanager


class PodcastState(Enum):
    INITIALIZED = 0
    TRANSCRIPT_BUILT = 1
    AUDIO_SEGMENTS_BUILT = 2
    ASSEMBLED = 3


class LLMBackend(ABC):
    @abstractmethod
    def generate_text(self, prompt: str) -> str:
        pass


class TTSBackend(ABC):
    @abstractmethod
    def text_to_speech(self, text: str, voice: str) -> Path:
        pass


class TranscriptSegment:
    def __init__(self, text: str, speaker: str, tts_args: Optional[Dict[str, Any]] = None):
        self.text = text
        self.speaker = speaker
        self.tts_args = tts_args or {}


class Transcript:
    def __init__(self, segments: List[TranscriptSegment], metadata: Dict[str, Any]):
        self.segments = segments
        self.metadata = metadata

    def save(self, filepath: str, format: str = "plaintext"):
        with open(filepath, 'w') as f:
            f.write(str(self))

    def __str__(self) -> str:
        lines = []
        for segment in self.segments:
            lines.append(f"{segment.speaker}: {segment.text}")

        metadata_str = "\n".join([f"{key}: {value}" for key, value in self.metadata.items()])

        return f"Metadata:\n{metadata_str}\n\nTranscript:\n" + "\n".join(lines)


class AudioSegment:
    def __init__(self, filepath: Path, length_ms: int, transcript_segment: Optional[TranscriptSegment] = None):
        self.filepath = filepath
        self.length_ms = length_ms
        self.transcript_segment = transcript_segment
        self._audio: Optional[PydubAudioSegment] = None

    @property
    def audio(self) -> PydubAudioSegment:
        if self._audio is None:
            self._audio = PydubAudioSegment.from_file(self.filepath)
            if len(self._audio) != self.length_ms:
                raise ValueError(
                    f"Audio file length ({len(self._audio)}ms) does not match specified length ({self.length_ms}ms)")
        return self._audio


def podcast_stage(target_state: PodcastState):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if self.state.value >= target_state.value and not self._reworking:
                print(f"Stage {target_state.name} has already been completed. Skipping.")
                return
            elif self.state.value + 1 != target_state.value and not self._reworking:
                raise ValueError(
                    f"Cannot skip stages. Current state: {self.state.name}, Target state: {target_state.name}")

            try:
                result = func(self, *args, **kwargs)
                self.state = target_state
                return result
            except Exception as e:
                print(f"Error in {func.__name__}: {str(e)}")
                raise

        return wrapper

    return decorator


class Podcast:
    def __init__(self, content: str, llm_backend: LLMBackend, tts_backend: TTSBackend):
        self.content = content
        self.llm_backend = llm_backend
        self.tts_backend = tts_backend
        self.reset_to_state(PodcastState.INITIALIZED)
        self._reworking = False

        self._stage_methods: Dict[PodcastState, Callable[[], None]] = {
            PodcastState.INITIALIZED: self.build_transcript,
            PodcastState.TRANSCRIPT_BUILT: self.build_audio_segments,
            PodcastState.AUDIO_SEGMENTS_BUILT: self.assemble_audio_segments,
            PodcastState.ASSEMBLED: lambda: None,
        }

    def reset_to_state(self, state: PodcastState):
        self.state = state
        self.transcript = None if state.value < PodcastState.TRANSCRIPT_BUILT.value else self.transcript
        self.audio_segments = [] if state.value < PodcastState.AUDIO_SEGMENTS_BUILT.value else self.audio_segments
        self.assembled_audio = None if state.value < PodcastState.ASSEMBLED.value else self.assembled_audio

    @contextmanager
    def rework(self, target_state: PodcastState, auto_finalize: bool = True):
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

    @podcast_stage(PodcastState.TRANSCRIPT_BUILT)
    def build_transcript(self) -> None:
        generated_text = self.llm_backend.generate_text(self.content)

        segments = [
            TranscriptSegment(line.split(": ")[1], line.split(": ")[0])
            for line in generated_text.split("\n") if ": " in line
        ]

        self.transcript = Transcript(segments, {"source": "Generated content"})

    @podcast_stage(PodcastState.AUDIO_SEGMENTS_BUILT)
    def build_audio_segments(self) -> None:
        self.audio_segments = []
        for segment in self.transcript.segments:
            audio_file = self.tts_backend.text_to_speech(segment.text, segment.speaker)
            audio_segment = PydubAudioSegment.from_file(audio_file)
            self.audio_segments.append(AudioSegment(audio_file, len(audio_segment), segment))

    @podcast_stage(PodcastState.ASSEMBLED)
    def assemble_audio_segments(self) -> None:
        self.assembled_audio = sum([segment.audio for segment in self.audio_segments])

    def _build_next_stage(self) -> bool:
        if self.state == PodcastState.ASSEMBLED:
            return False

        next_method = self._stage_methods[self.state]
        next_method()
        return True

    def finalize(self) -> None:
        while self._build_next_stage():
            pass

    def save(self, filepath: str) -> None:
        if self.state != PodcastState.ASSEMBLED:
            raise ValueError("Podcast can only be saved after audio is assembled")

        if self.assembled_audio:
            self.assembled_audio.export(filepath, format="mp3")
        else:
            raise ValueError("No assembled audio to save")

    def save_transcript(self, filepath: str, format: str = "plaintext") -> None:
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
        def generate_text(self, prompt: str) -> str:
            return "Host: Welcome to our podcast!\nGuest: Thanks for having me!"


    class DummyTTSBackend(TTSBackend):
        def text_to_speech(self, text: str, voice: str) -> Path:
            with NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
                PydubAudioSegment.silent(duration=1000).export(temp_file.name, format="mp3")
            return Path(temp_file.name)



    # Initialize the podcast
    podcast = Podcast(
        content="""
        This is a sample content for our podcast.
        It includes information from multiple sources that have already been parsed.
        """,
        llm_backend=DummyLLMBackend(),
        tts_backend=DummyTTSBackend(),
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

    # Step 3: Assemble audio segments
    podcast.assemble_audio_segments()
    print(f"After assembling audio: {podcast.state}")

    # Rework example: modify the transcript and rebuild (auto_finalize is True by default)
    with podcast.rework(PodcastState.TRANSCRIPT_BUILT):
        print(f"Inside rework context, state: {podcast.state}")
        podcast.transcript.segments.append(TranscriptSegment("This is a new segment", "Host"))
        print("Added new segment to transcript")

        # Rebuild audio segments and assemble
        podcast.build_audio_segments()

    print(f"After rework: {podcast.state}")

    # Add a new audio segment (auto_finalize is True by default)
    with NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
        PydubAudioSegment.silent(duration=500).export(temp_file.name, format="mp3")
    
    with podcast.rework(PodcastState.AUDIO_SEGMENTS_BUILT):
        new_segment = AudioSegment(Path(temp_file.name), 500, TranscriptSegment("New audio segment", "Host"))
        podcast.audio_segments.insert(0, new_segment)

    # Save the final podcast
    podcast.save("./final.mp3")
    podcast.save_transcript("./final.txt", format="plaintext")
    print("Saved podcast and transcript")
