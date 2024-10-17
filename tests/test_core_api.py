"""Tests for the core API of the podcastfy package. Not e2e tests as DummyTTSBackend is used to simulate the TTS backend and DummyLLMBackend is used to simulate the LLM backend."""
import pytest
from pathlib import Path
from pydub import AudioSegment

from podcastfy.core.content import Content
from podcastfy.core.podcast import Podcast, PodcastState
from podcastfy.aiengines.llm.base import LLMBackend
from podcastfy.core.character import Character
from podcastfy.core.tts_configs import TTSConfig
from podcastfy.core.transcript import TranscriptSegment, Transcript
from podcastfy.core.audio import AudioManager

class DummyLLMBackend(LLMBackend):
    def generate_transcript(self, content, characters):
        return [
            (characters[0], "Welcome to our podcast!"),
            (characters[1], "Thanks for having me!")
        ]

class DummyTTSBackend:
    def __init__(self, name: str):
        self.name = name

    def text_to_speech(self, text: str, character: Character, output_path: Path) -> Path:
        audio = AudioSegment.silent(duration=1000)
        audio.export(str(output_path), format="mp3")
        return output_path

@pytest.fixture
def audio_manager(tmp_path):
    tts_backends = {"openai": DummyTTSBackend("openai"), "elevenlabs": DummyTTSBackend("elevenlabs")}
    return AudioManager(tts_backends, audio_format="mp3", audio_temp_dir=tmp_path, n_jobs=1)

@pytest.fixture
def characters():
    host = Character(
        name="Person1",
        role="Podcast host",
        tts_configs={
            "openai": TTSConfig(voice="en-US-Neural2-F", backend="openai", extra_args={"speaking_rate": 1.0}),
            "elevenlabs": TTSConfig(voice="Rachel", backend="elevenlabs", extra_args={"stability": 0.5})
        },
        default_description_for_llm="{name} is an enthusiastic podcast host. Speaks clearly and engagingly."
    )

    guest = Character(
        name="Person2",
        role="Expert guest",
        tts_configs={
            "openai": TTSConfig(voice="en-US-Neural2-D", backend="openai", extra_args={"pitch": -2.0}),
            "elevenlabs": TTSConfig(voice="Antoni", backend="elevenlabs", extra_args={"stability": 0.8})
        },
        default_description_for_llm="{name} is an expert guest. Shares knowledge in a friendly manner."
    )

    return [host, guest]

@pytest.fixture
def podcast(audio_manager, characters):
    return Podcast(
        content=[Content(value="This is a sample content for our podcast.", type="text")],
        llm_backend=DummyLLMBackend(),
        audio_manager=audio_manager,
        characters=characters,
    )

def test_podcast_initialization(podcast):
    assert podcast.state == PodcastState.INITIALIZED
    assert podcast.transcript is None
    assert podcast.audio is None

def test_build_transcript(podcast):
    podcast.build_transcript()
    assert podcast.state == PodcastState.TRANSCRIPT_BUILT
    assert isinstance(podcast.transcript, Transcript)
    assert len(podcast.transcript.segments) == 2

def test_build_audio_segments(podcast):
    podcast.build_transcript()
    podcast.build_audio_segments()
    assert podcast.state == PodcastState.AUDIO_SEGMENTS_BUILT
    assert len(podcast.audio_segments) == 2

def test_stitch_audio_segments(podcast):
    podcast.build_transcript()
    podcast.build_audio_segments()
    podcast.stitch_audio_segments()
    assert podcast.state == PodcastState.STITCHED
    assert isinstance(podcast.audio, AudioSegment)

def test_finalize(podcast):
    podcast.finalize()
    assert podcast.state == PodcastState.STITCHED
    assert isinstance(podcast.transcript, Transcript)
    assert len(podcast.audio_segments) > 0
    assert isinstance(podcast.audio, AudioSegment)

def test_save(podcast, tmp_path):
    podcast.finalize()
    output_file = tmp_path / "test_podcast.mp3"
    podcast.save(str(output_file))
    assert output_file.exists()

def test_export_transcript(podcast, tmp_path):
    podcast.finalize()
    output_file = tmp_path / "test_transcript.txt"
    podcast.export_transcript(str(output_file), format_="plaintext")
    assert output_file.exists()

def test_rework(podcast):
    podcast.finalize()

    with podcast.rework(PodcastState.TRANSCRIPT_BUILT):
        assert podcast.state == PodcastState.TRANSCRIPT_BUILT
        podcast.transcript.segments.append(
            TranscriptSegment("This is a new segment", podcast.characters["Person1"]))

    assert podcast.state == PodcastState.STITCHED
    assert len(podcast.transcript.segments) == 3

def test_from_transcript(audio_manager, characters):
    pre_existing_transcript = [
        ("Person1", "Welcome to our podcast created from a pre-existing transcript!"),
        ("Person2", "Thank you for having me. I'm excited to be here.")
    ]

    podcast = Podcast.from_transcript(
        transcript=Transcript([
            TranscriptSegment(text, characters[0] if speaker == "Person1" else characters[1])
            for speaker, text in pre_existing_transcript
        ]),
        audio_manager=audio_manager,
        characters=characters
    )

    assert podcast.state == PodcastState.TRANSCRIPT_BUILT
    assert len(podcast.transcript.segments) == 2

    podcast.finalize()
    assert podcast.state == PodcastState.STITCHED

def test_load_transcript(audio_manager, characters, tmp_path):
    # Create a dummy transcript file
    transcript_file = tmp_path / "test_transcript.json"
    Transcript([
        TranscriptSegment("Welcome to our podcast!", characters[0]),
        TranscriptSegment("Thank you for having me!", characters[1])
    ]).dump(str(transcript_file))

    podcast = Podcast.load_transcript(str(transcript_file), audio_manager, characters)
    assert podcast.state == PodcastState.TRANSCRIPT_BUILT
    assert len(podcast.transcript.segments) == 2