import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from tempfile import TemporaryFile, TemporaryDirectory
from typing import Dict, Any, List, ClassVar
import asyncio

import openai

from podcastfy.character import Character, VoiceConfig
import edge_tts
from elevenlabs import client as elevenlabs_client

class TTSBackend(ABC):
    name: ClassVar[str] = ""
    default_voices: ClassVar[List[VoiceConfig]] = []

    @classmethod
    def set_default_voices(cls, voices: List[VoiceConfig]):
        """
        Set the default voices for the TTS backend.
        """
        cls.default_voices = voices

    @abstractmethod
    def text_to_speech(self, text: str, character: Character, output_path: Path) -> Path:
        """
        Convert text to speech.

        Args:
            text (str): The text to convert to speech.
            character (Character): The character for which to generate speech.
            output_path (Path): The path where the audio file should be saved.

        Returns:
            Path: Path to the generated audio file (same as output_path).
        """
        pass

class ElevenLabsTTS(TTSBackend):
    name: str = "elevenlabs"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")

    def text_to_speech(self, text: str, character: Character, output_path: Path) -> Path:
        # TODO, would be nicer to get a filepath directly from the client
        config = character.get_tts_args('elevenlabs')
        client = elevenlabs_client.ElevenLabs(api_key=self.api_key)  # # client could be reused
        content = client.generate(
            text=text,
            voice=config.voice,
            model=config.extra_args.get('model', 'default')
        )
        with open(output_path, "wb") as out:
            for chunk in content:
                if chunk:
                    out.write(chunk)
        return output_path

class OpenAITTS(TTSBackend):
    name: str = "openai"
    def __init__(self, api_key: str):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

    def ensure_characters_tts_config_is_valid(self, character:Character) -> None:
        # TODO: maybe that should be in the ABC class
        tts_config = character.tts_configs.get('openai')
        if not tts_config:
            raise ValueError(f"Character '{character.name}' does not have OpenAI TTS configuration")
        # ensure there is a key model in the extra_args
        if 'model' not in tts_config.extra_args:
            raise ValueError(f"Character '{character.name}' does not have the 'model' key in the OpenAI TTS configuration")


    def text_to_speech(self, text: str, character: Character, output_path: Path) -> Path:
        # TODO, would be nicer to get a filepath directly from the client. If not given takes tempdir from the config ?
        self.ensure_characters_tts_config_is_valid(character)
        # Placeholder for OpenAI TTS implementation
        config = character.get_tts_args('openai')

        print(f"OpenAI TTS: Converting text to speech for character {character.name} with voice {config.voice}")
        response = openai.audio.speech.create(
            model=config.extra_args["model"],
            voice=config.voice,
            input=text
        )
        with open(output_path, "wb") as file:
            file.write(response.content)
        return output_path

class EdgeTTS(TTSBackend):
    name: str = "edge-tts"


    def __init__(self):
        pass

    def text_to_speech(self, text: str, character: Character, output_path: Path) -> Path:
        config = character.get_tts_args('edge-tts')

        async def edge_tts_conversion(text: str, output_path: str, voice: str):
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)

        asyncio.run(edge_tts_conversion(text, str(output_path), config.voice))

        return output_path


    def ensure_characters_tts_config_is_valid(self, character: Character) -> None:
        tts_config = character.tts_configs.get('edge-tts')
        if not tts_config:
            raise ValueError(f"Character '{character.name}' does not have Edge TTS configuration")

# Example usage:
if __name__ == "__main__":
    from podcastfy.utils.config import load_config

    config = load_config()
    elevenlabs_tts = ElevenLabsTTS(config.ELEVENLABS_API_KEY, config.get('text_to_speech', {}).get('elevenlabs', {}))
    openai_tts = OpenAITTS(config.OPENAI_API_KEY, config.get('text_to_speech', {}).get('openai', {}))
    # edge_tts = EdgeTTS()

    dummy_character = Character("John", "host", {
        'elevenlabs': {'voice': 'en-US-JohnNeural'},
        'openai': {'voice': 'en-US-Neural2-C'},
        'edge-tts': {'voice': 'en-US-ChristopherNeural'}
    }, "A friendly podcast host")

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"{dummy_character.name}_{uuid.uuid4().hex}.mp3"
    elevenlabs_tts.text_to_speech("Hello, welcome to the podcast!", dummy_character, output_path)
