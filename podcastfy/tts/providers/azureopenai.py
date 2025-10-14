"""OpenAI TTS provider implementation."""

from openai import AzureOpenAI
from typing import List, Optional
from ..base import TTSProvider
import os

class Azure_OpenAITTS(TTSProvider):
    """OpenAI Text-to-Speech provider."""
    
    # Provider-specific SSML tags
    PROVIDER_SSML_TAGS: List[str] = ['break', 'emphasis']

    client: AzureOpenAI
    
    def __init__(self, api_key: Optional[str] = None, model: str = "tts-1-hd"):
        """
        Initialize OpenAI TTS provider.
        
        Args:
            api_key: OpenAI API key. If None, expects OPENAI_API_KEY env variable
            model: Model name to use. Defaults to "tts-1-hd"
        """

        if not api_key and not os.environ.get("AZURE_OPENAI_API_KEY"):
            raise ValueError("Azure OpenAI API key must be provided or set in environment")
        
        if not os.environ.get("AZURE_OPENAI_ENDPOINT"):
            raise ValueError("Azure OpenAI API base URL must be set in environment")
        
        self.client = AzureOpenAI(
            api_key=api_key or os.environ["AZURE_OPENAI_API_KEY"],
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_version="2024-05-01-preview"
        )

        self.model = model
            
    def get_supported_tags(self) -> List[str]:
        """Get all supported SSML tags including provider-specific ones."""
        return self.PROVIDER_SSML_TAGS
        
    def generate_audio(self, text: str, voice: str, model: str, voice2: str = None) -> bytes:
        """Generate audio using OpenAI API."""
        self.validate_parameters(text, voice, model)
        
        try:
            response = self.client.audio.speech.create(
                model=model,
                voice=voice,
                input=text
            )
            return response.content
        except Exception as e:
            raise RuntimeError(f"Failed to generate audio: {str(e)}") from e