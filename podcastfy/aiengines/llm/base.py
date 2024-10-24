from abc import ABC, abstractmethod
from typing import List, Tuple

from podcastfy.core.character import Character
from podcastfy.core.content import Content


class LLMBackend(ABC):
    """Abstract base class for Language Model backends."""
    # TODO a nice mixin/helper could be made to load prompt templates from conf file (both podcast settings and character settings)

    @abstractmethod
    def generate_transcript(self, content: List[Content], characters: List[Character]) -> List[Tuple[Character, str]]:
        """
        Generate text based on a given prompt.

        Args:
            prompt (str): The input prompt for text generation.

        Returns:
            List[Tuple[Character, str]]: A list of tuples containing speaker and text.
        """
        pass
