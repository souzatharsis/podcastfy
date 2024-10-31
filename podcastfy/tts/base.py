"""Abstract base class for Text-to-Speech providers."""

from abc import ABC, abstractmethod
from typing import List, Set, ClassVar

class TTSProvider(ABC):
    """Abstract base class that defines the interface for TTS providers."""
    
    # Common SSML tags supported by most providers
    COMMON_SSML_TAGS: ClassVar[Set[str]] = {
        'lang', 'p', 'phoneme', 's', 'say-as', 'sub'
    }
    
    @abstractmethod
    def generate_audio(self, text: str, voice: str, model: str) -> bytes:
        """
        Generate audio from text using the provider's API.
        
        Args:
            text: Text to convert to speech
            voice: Voice ID/name to use
            model: Model ID/name to use
            
        Returns:
            Audio data as bytes
            
        Raises:
            ValueError: If invalid parameters are provided
            RuntimeError: If audio generation fails
        """
        pass

    def get_supported_tags(self) -> Set[str]:
        """
        Get set of SSML tags supported by this provider.
        
        Returns:
            Set of supported SSML tag names
        """
        return self.COMMON_SSML_TAGS.copy()
    
    def validate_parameters(self, text: str, voice: str, model: str) -> None:
        """
        Validate input parameters before generating audio.
        
        Raises:
            ValueError: If any parameter is invalid
        """
        if not text:
            raise ValueError("Text cannot be empty")
        if not voice:
            raise ValueError("Voice must be specified")
        if not model:
            raise ValueError("Model must be specified")