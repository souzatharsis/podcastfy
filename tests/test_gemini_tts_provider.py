from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from podcastfy.tts.providers.gemini import GeminiTTS


@pytest.fixture
def gemini_client():
    client = Mock()
    client.synthesize_speech.return_value = SimpleNamespace(audio_content=b"audio")
    with patch(
        "podcastfy.tts.providers.gemini.texttospeech_v1beta1.TextToSpeechClient",
        return_value=client,
    ):
        yield client


def test_generate_audio_passes_model_name_for_non_english_voice(gemini_client):
    provider = GeminiTTS(
        api_key="test-key",
        model="gemini-2.5-pro-tts",
    )

    audio = provider.generate_audio(
        "你好，欢迎收听。",
        voice="Algieba",
    )

    assert audio == b"audio"
    request = gemini_client.synthesize_speech.call_args.kwargs
    assert request["voice"].name == "Algieba"
    assert request["voice"].model_name == "gemini-2.5-pro-tts"
    assert request["input"].text == "你好，欢迎收听。"


def test_generate_audio_rejects_empty_text_before_provider_call(gemini_client):
    provider = GeminiTTS(api_key="test-key", model="gemini-2.5-pro-tts")

    with pytest.raises(ValueError, match="Text cannot be empty"):
        provider.generate_audio("", voice="Algieba")

    gemini_client.synthesize_speech.assert_not_called()
