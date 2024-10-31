"""OpenAI TTS provider implementation."""

import openai
from typing import Set, Optional
from ..base import TTSProvider

class OpenAITTS(TTSProvider):
    """OpenAI Text-to-Speech provider."""
    
    # Provider-specific SSML tags
    PROVIDER_SSML_TAGS: Set[str] = {'break', 'emphasis'}
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI TTS provider.
        
        Args:
            api_key: OpenAI API key. If None, expects OPENAI_API_KEY env variable
        """
        if api_key:
            openai.api_key = api_key
        elif not openai.api_key:
            raise ValueError("OpenAI API key must be provided or set in environment")
            
    def get_supported_tags(self) -> Set[str]:
        """Get all supported SSML tags including provider-specific ones."""
        return self.COMMON_SSML_TAGS | self.PROVIDER_SSML_TAGS
        
    def generate_audio(self, text: str, voice: str, model: str) -> bytes:
        """Generate audio using OpenAI API."""
        self.validate_parameters(text, voice, model)
        
        try:
            response = openai.audio.speech.create(
                model=model,
                voice=voice,
                input=text
            )
            return response.content
        except Exception as e:
            raise RuntimeError(f"Failed to generate audio: {str(e)}") from e