"""Factory for creating TTS providers."""

from typing import Dict, Type, Optional
from .base import TTSProvider
# from .providers.elevenlabs import ElevenLabsTTS  # Removed elevenlabs support
from .providers.openai import OpenAITTS
from .providers.edge import EdgeTTS
from .providers.gemini import GeminiTTS
from .providers.geminimulti import GeminiMultiTTS
from .providers.gemininew import GeminiNewTTS

class TTSProviderFactory:
    """Factory class for creating TTS providers."""
    
    _providers: Dict[str, Type[TTSProvider]] = {
        # 'elevenlabs': ElevenLabsTTS,  # Removed elevenlabs support
        'openai': OpenAITTS,
        'edge': EdgeTTS,
        'gemini': GeminiTTS,
        'geminimulti': GeminiMultiTTS,
        'gemininew': GeminiNewTTS
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
        
        # Special handling for gemininew to avoid passing provider name as model
        if provider_name.lower() == 'gemininew':
            # For gemininew, only pass model if it's a valid Gemini model name
            if model and model.startswith('gemini-') and 'tts' in model.lower():
                return provider_class(api_key, model) if api_key else provider_class(model=model)
            else:
                # Use the provider's default model
                return provider_class(api_key) if api_key else provider_class()
        else:
            # For other providers, use the original logic
            return provider_class(api_key, model) if api_key else provider_class(model=model)
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[TTSProvider]) -> None:
        """Register a new provider class."""
        cls._providers[name.lower()] = provider_class
    
    @classmethod
    def get_available_providers(cls) -> Dict[str, Type[TTSProvider]]:
        """Get all available provider classes."""
        return cls._providers.copy() 