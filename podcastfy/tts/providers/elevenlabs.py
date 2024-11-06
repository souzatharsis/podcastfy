"""ElevenLabs TTS provider implementation."""

from elevenlabs import client as elevenlabs_client
from ..base import TTSProvider
from typing import List

class ElevenLabsTTS(TTSProvider):
    def __init__(self, api_key: str, model: str = "eleven_multilingual_v2"):
        """
        Initialize ElevenLabs TTS provider.
        
        Args:
            api_key (str): ElevenLabs API key
            model (str): Model name to use. Defaults to "eleven_multilingual_v2"
        """
        self.client = elevenlabs_client.ElevenLabs(api_key=api_key)
        self.model = model
        
    def generate_audio(self, text: str, voice: str, model: str, voice2: str = None) -> bytes:
        """Generate audio using ElevenLabs API."""
        audio = self.client.generate(
            text=text,
            voice=voice,
            model=model
        )
        return b''.join(chunk for chunk in audio if chunk)
        
    def get_supported_tags(self) -> List[str]:
        """Get supported SSML tags."""
        return ['lang', 'p', 'phoneme', 's', 'sub'] 