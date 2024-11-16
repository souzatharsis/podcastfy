"""Abstract base class for Text-to-Speech providers."""

from abc import ABC, abstractmethod
from typing import List, ClassVar, Tuple
import re

class TTSProvider(ABC):
    """Abstract base class that defines the interface for TTS providers."""
    
    # Common SSML tags supported by most providers
    COMMON_SSML_TAGS: ClassVar[List[str]] = [
        'lang', 'p', 'phoneme', 's', 'sub'
    ]
    
    @abstractmethod
    def generate_audio(self, text: str, voice: str, model: str, voice2: str) -> bytes:
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

    def get_supported_tags(self) -> List[str]:
        """
        Get set of SSML tags supported by this provider.
        
        Returns:
            Set of supported SSML tag names
        """
        return self.COMMON_SSML_TAGS.copy()
    
    def validate_parameters(self, text: str, voice: str, model: str, voice2: str = None) -> None:
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
        
    def split_qa(self, input_text: str, ending_message: str, supported_tags: List[str] = None) -> List[Tuple[str, str]]:
        """
        Split the input text into question-answer pairs.

        Args:
            input_text (str): The input text containing Person1 and Person2 dialogues.
            ending_message (str): The ending message to add to the end of the input text.

        Returns:
                List[Tuple[str, str]]: A list of tuples containing (Person1, Person2) dialogues.
        """
        input_text = self.clean_tss_markup(input_text, supported_tags=supported_tags)
        
        # Add placeholder if input_text starts with <Person2>
        if input_text.strip().startswith("<Person2>"):
            input_text = "<Person1> Humm... </Person1>" + input_text

        # Add ending message to the end of input_text
        if input_text.strip().endswith("</Person1>"):
            input_text += f"<Person2>{ending_message}</Person2>"

        # Regular expression pattern to match Person1 and Person2 dialogues
        pattern = r"<Person1>(.*?)</Person1>\s*<Person2>(.*?)</Person2>"

        # Find all matches in the input text
        matches = re.findall(pattern, input_text, re.DOTALL)

        # Process the matches to remove extra whitespace and newlines
        processed_matches = [
            (" ".join(person1.split()).strip(), " ".join(person2.split()).strip())
            for person1, person2 in matches
        ]
        return processed_matches

    def clean_tss_markup(self, input_text: str, additional_tags: List[str] = ["Person1", "Person2"], supported_tags: List[str] = None) -> str:
        """
        Remove unsupported TSS markup tags from the input text while preserving supported SSML tags.

        Args:
            input_text (str): The input text containing TSS markup tags.
            additional_tags (List[str]): Optional list of additional tags to preserve. Defaults to ["Person1", "Person2"].
            supported_tags (List[str]): Optional list of supported tags. If None, use COMMON_SSML_TAGS.
        Returns:
            str: Cleaned text with unsupported TSS markup tags removed.
        """
        if supported_tags is None:
            supported_tags = self.COMMON_SSML_TAGS.copy()

        # Append additional tags to the supported tags list
        supported_tags.extend(additional_tags)

        # Create a pattern that matches any tag not in the supported list
        pattern = r'</?(?!(?:' + '|'.join(supported_tags) + r')\b)[^>]+>'

        # Remove unsupported tags
        cleaned_text = re.sub(pattern, '', input_text)

        # Remove any leftover empty lines
        cleaned_text = re.sub(r'\n\s*\n', '\n', cleaned_text)

        # Ensure closing tags for additional tags are preserved
        for tag in additional_tags:
            cleaned_text = re.sub(f'<{tag}>(.*?)(?=<(?:{"|".join(additional_tags)})>|$)', 
                                f'<{tag}>\\1</{tag}>', 
                                cleaned_text, 
                                flags=re.DOTALL)

        return cleaned_text.strip()