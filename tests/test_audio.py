import pytest
import os
from pathlib import Path
from podcastfy.core.character import Character
from podcastfy.aiengines.tts.tts_backends import ElevenLabsTTS, OpenAITTS, EdgeTTS

@pytest.fixture
def test_setup():
    test_text = "<Person1>Hello, how are you?</Person1><Person2>I'm doing great, thanks for asking!</Person2>"
    output_dir = Path("tests/data/audio")
    output_dir.mkdir(parents=True, exist_ok=True)
    dummy_character = Character("test_character", "host", {}, "A test character")
    return test_text, output_dir, dummy_character

@pytest.mark.skip(reason="Testing Eleven Labs only on Github Action as it requires API key")
def test_text_to_speech_elevenlabs(test_setup):
    test_text, output_dir, dummy_character = test_setup
    tts = ElevenLabsTTS()
    output_file = output_dir / "test_elevenlabs.mp3"
    tts.text_to_speech(test_text, dummy_character, output_file)

    assert output_file.exists()
    assert output_file.stat().st_size > 0

    # Clean up
    output_file.unlink()

@pytest.mark.skip(reason="Testing OpenAI only on Github Action as it requires API key")
def test_text_to_speech_openai(test_setup):
    test_text, output_dir, dummy_character = test_setup
    tts = OpenAITTS()
    output_file = output_dir / "test_openai.mp3"
    tts.text_to_speech(test_text, dummy_character, output_file)

    assert output_file.exists()
    assert output_file.stat().st_size > 0

    # Clean up
    output_file.unlink()

@pytest.mark.asyncio
async def test_text_to_speech_edge(test_setup):
    test_text, output_dir, dummy_character = test_setup
    tts = EdgeTTS()
    output_file = output_dir / "test_edge.mp3"
    await tts.async_text_to_speech(test_text, dummy_character, output_file)

    assert output_file.exists()
    assert output_file.stat().st_size > 0

    # Clean up
    output_file.unlink()