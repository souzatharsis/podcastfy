"""ElevenLabs TTS provider implementation."""

from elevenlabs import client as elevenlabs_client
from ..base import TTSProvider
from typing import List

class ElevenLabsTTS(TTSProvider):
    def __init__(self, api_key: str):
        """
        Initialize ElevenLabs TTS provider.
        
        Args:
            api_key (str): ElevenLabs API key
        """
        self.client = elevenlabs_client.ElevenLabs(api_key=api_key)
        
    def generate_audio(self, text: str, voice: str, model: str) -> bytes:
        """Generate audio using ElevenLabs API."""
        audio = self.client.generate(
            text=text,
            voice=voice,
            model=model
        )
        return b''.join(chunk for chunk in audio if chunk)
        
    def get_supported_tags(self) -> List[str]:
        """Get supported SSML tags."""
        return ['lang', 'p', 'phoneme', 's', 'say-as', 'sub'] 