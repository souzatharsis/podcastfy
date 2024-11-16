"""Factory for creating TTS providers."""

from typing import Dict, Type, Optional
from .base import TTSProvider
from .providers.elevenlabs import ElevenLabsTTS
from .providers.openai import OpenAITTS
from .providers.edge import EdgeTTS
from .providers.gemini import GeminiTTS
from .providers.geminimulti import GeminiMultiTTS
class TTSProviderFactory:
    """Factory class for creating TTS providers."""
    
    _providers: Dict[str, Type[TTSProvider]] = {
        'elevenlabs': ElevenLabsTTS,
        'openai': OpenAITTS,
        'edge': EdgeTTS,
        'gemini': GeminiTTS,
        'geminimulti': GeminiMultiTTS
    }
    
    @classmethod
    def create(cls, provider_name: str, api_key: Optional[str] = None, model: Optional[str] = None) -> TTSProvider:
        """
        Create a TTS provider instance.
        
        Args:
            provider_name: Name of the provider to create
            api_key: Optional API key for the provider
            model: Optional model name for the provider
            
        Returns:
            TTSProvider instance
            
        Raises:
            ValueError: If provider_name is not supported
        """
        provider_class = cls._providers.get(provider_name.lower())
        if not provider_class:
            raise ValueError(f"Unsupported provider: {provider_name}. "
                           f"Choose from: {', '.join(cls._providers.keys())}")
                           
        return provider_class(api_key, model) if api_key else provider_class(model=model)
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[TTSProvider]) -> None:
        """Register a new provider class."""
        cls._providers[name.lower()] = provider_class 