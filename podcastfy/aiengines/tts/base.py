from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Union

import yaml

from podcastfy.core.character import Character
from podcastfy.core.tts_configs import TTSConfig

TTSBackend = Union["SyncTTSBackend", "AsyncTTSBackend"]


class SyncTTSBackend(ABC):
    """Protocol for synchronous Text-to-Speech backends."""

    name: str

    @abstractmethod
    def text_to_speech(self, text: str, character: Character, output_path: Path) -> None:
        """
        Convert text to speech synchronously.

        Args:
            text (str): The text to convert to speech.
            character (Character): The character for which to generate speech.
            output_path (Path): The path to save the generated audio file.

        Returns:
            Path: The path to the generated audio file.
        """
        pass


class AsyncTTSBackend(ABC):
    """Protocol for asynchronous Text-to-Speech backends."""

    name: str

    @abstractmethod
    async def async_text_to_speech(self, text: str, character: Character, output_path: Path) -> None:
        """
        Convert text to speech asynchronously.

        Args:
            text (str): The text to convert to speech.
            character (Character): The character for which to generate speech.
            output_path (Path): The path to save the generated audio file.

        Returns:
            Path: The path to the generated audio file.
        """
        pass
class TTSConfigMixin:
    """Mixin class to manage TTS external configurations."""

    def __init__(self, config_file: str = 'podcastfy/conversation_config.yaml', name: str = "") -> None:
        self.name = name
        self.config_file = config_file
        self.default_configs = self._load_default_configs()
        self.tts_config_call_count = 0
        self.character_tts_mapping = {}

    def _load_default_configs(self) -> Dict[str, Any]:
        with open(self.config_file, 'r') as f:
            config = yaml.safe_load(f)
        tts_config = config.get('text_to_speech', {})
        return tts_config.get(self.name, {})

    def get_default_config(self) -> Dict[str, Any]:
        return self.default_configs

    def update_default_config(self, new_config: Dict[str, Any]) -> None:
        self.default_configs.update(new_config)

    def tts_config_for_character(self, character: Character) -> TTSConfig:
        # note: a bit constrained by the fact that the config has just the question and answer fields
        if character.name in self.character_tts_mapping:
            return self.character_tts_mapping[character.name]

        # Check if the character has a TTS config for this backend
        if self.name in character.tts_configs:
            tts_config = character.tts_configs[self.name]
        else:
            # If not, use the default config
            default_voices = self.default_configs.get('default_voices', {})
            if self.tts_config_call_count == 0:
                voice = default_voices['question']
            else:
                voice = default_voices['answer']
            model = self.default_configs.get('model')
            self.tts_config_call_count += 1

            tts_config = TTSConfig(
                voice=voice,
                backend=self.name,
                extra_args={"model": model} if model else {}
            )

        # Merge the default config with the character-specific config
        merged_config = TTSConfig(
            voice=tts_config.voice or self.default_configs.get('default_voices', {}).get('question' if self.tts_config_call_count == 1 else 'answer', ''),
            backend=self.name,
            extra_args={**self.default_configs.get('extra_args', {}), **tts_config.extra_args}
        )

        self.character_tts_mapping[character.name] = merged_config
        return merged_config

        # This line is no longer needed as we always return a merged config

    def preload_character_tts_mapping(self, characters: List[Character]) -> None:
        for character in characters:
            self.tts_config_for_character(character)

    def get_character_tts_mapping(self) -> Dict[str, TTSConfig]:
        return self.character_tts_mapping
