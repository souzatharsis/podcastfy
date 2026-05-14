"""Typecast TTS provider implementation."""

from typecast import Typecast
from typecast.models import TTSRequest, Output
from ..base import TTSProvider
from typing import List


class TypecastTTS(TTSProvider):
    def __init__(self, api_key: str, model: str = "ssfm-v30"):
        self.client = Typecast(api_key=api_key)
        self.model = model

    def generate_audio(self, text: str, voice: str, model: str, voice2: str = None) -> bytes:
        """Generate audio using Typecast API."""
        response = self.client.text_to_speech(TTSRequest(
            text=text,
            model=model,
            voice_id=voice,
            output=Output(audio_format="mp3"),
        ))
        return response.audio_data

    def get_supported_tags(self) -> List[str]:
        return ['lang', 'p', 'phoneme', 's', 'sub']
