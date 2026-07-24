import unittest
import pytest
import os
import base64
from unittest.mock import patch, MagicMock
from podcastfy.text_to_speech import TextToSpeech
from podcastfy.tts.providers.edenai import EdenAITTS
from podcastfy.utils.config_conversation import load_conversation_config


class TestAudio(unittest.TestCase):
    def setUp(self):
        self.test_text = "<Person1>Hello, how are you?</Person1><Person2>I'm doing great, thanks for asking!</Person2>"
        self.output_dir = "tests/data/audio"
        os.makedirs(self.output_dir, exist_ok=True)

    @pytest.mark.skip(reason="Testing edge only on Github Action as it's free")
    def test_text_to_speech_openai(self):
        tts = TextToSpeech(model="openai")
        output_file = os.path.join(self.output_dir, "test_openai.mp3")
        tts.convert_to_speech(self.test_text, output_file)

        self.assertTrue(os.path.exists(output_file))
        self.assertGreater(os.path.getsize(output_file), 1024)

        # Clean up
        os.remove(output_file)

    @pytest.mark.skip(reason="Testing edge only on Github Action as it's free")
    def test_text_to_speech_elevenlabs(self):
        tts = TextToSpeech(model="elevenlabs")
        output_file = os.path.join(self.output_dir, "test_elevenlabs.mp3")
        tts.convert_to_speech(self.test_text, output_file)

        self.assertTrue(os.path.exists(output_file))
        self.assertGreater(os.path.getsize(output_file), 1024)

        # Clean up
        os.remove(output_file)

    def test_text_to_speech_edge(self):
        tts = TextToSpeech(model="edge")
        output_file = os.path.join(self.output_dir, "test_edge.mp3")
        tts.convert_to_speech(self.test_text, output_file)

        self.assertTrue(os.path.exists(output_file))
        self.assertGreater(os.path.getsize(output_file), 1024)

        # Clean up
        os.remove(output_file)

    @pytest.mark.skip(reason="Testing edge only on Github Action as it's free")
    def test_text_to_speech_google(self):
        tts = TextToSpeech(model="gemini")
        output_file = os.path.join(self.output_dir, "test_google.mp3")
        tts.convert_to_speech(self.test_text, output_file)

        self.assertTrue(os.path.exists(output_file))
        self.assertGreater(os.path.getsize(output_file), 1024)

        # Clean up
        os.remove(output_file)

    @pytest.mark.skip(reason="Testing edge only on Github Action as it's free")
    def test_text_to_speech_edenai(self):
        tts = TextToSpeech(model="edenai")
        output_file = os.path.join(self.output_dir, "test_edenai.mp3")
        tts.convert_to_speech(self.test_text, output_file)

        self.assertTrue(os.path.exists(output_file))
        self.assertGreater(os.path.getsize(output_file), 1024)

        # Clean up
        os.remove(output_file)

    @pytest.mark.skip(reason="Testing edge only on Github Action as it's free")
    def test_text_to_speech_google_multi(self):
        tts = TextToSpeech(model="gemini_multi")
        output_file = os.path.join(self.output_dir, "test_google_multi.mp3")
        tts.convert_to_speech(self.test_text, output_file)

        self.assertTrue(os.path.exists(output_file))
        self.assertGreater(os.path.getsize(output_file), 1024)

        # Clean up
        os.remove(output_file)


class TestEdenAITTS(unittest.TestCase):
    """Unit tests for the Eden AI provider that do not require network access."""

    def _mock_response(self, engine="openai"):
        fake_audio = base64.b64encode(b"fake-audio-bytes").decode()
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.json.return_value = {
            engine: {"status": "success", "audio": fake_audio}
        }
        return response

    @patch("podcastfy.tts.providers.edenai.requests.post")
    def test_gender_voice_uses_option(self, mock_post):
        mock_post.return_value = self._mock_response("openai")
        provider = EdenAITTS(api_key="test-key")
        audio = provider.generate_audio("Hello", "FEMALE", "openai")

        self.assertEqual(audio, b"fake-audio-bytes")
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["option"], "FEMALE")
        self.assertEqual(payload["providers"], "openai")
        self.assertNotIn("settings", payload)

    @patch("podcastfy.tts.providers.edenai.requests.post")
    def test_named_voice_uses_settings(self, mock_post):
        mock_post.return_value = self._mock_response("google")
        provider = EdenAITTS(api_key="test-key")
        provider.generate_audio("Hello", "en-US-Standard-A", "google")

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["settings"], {"google": "en-US-Standard-A"})
        self.assertNotIn("option", payload)

    def test_missing_api_key_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                EdenAITTS()


if __name__ == "__main__":
    unittest.main()
