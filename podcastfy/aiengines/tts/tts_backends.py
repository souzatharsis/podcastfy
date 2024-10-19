import os
import uuid
from abc import abstractmethod
from pathlib import Path
from tempfile import TemporaryFile, TemporaryDirectory
from typing import Dict, Any, List, ClassVar
import asyncio

import openai

import edge_tts
from elevenlabs import client as elevenlabs_client

from podcastfy.aiengines.tts.base import SyncTTSBackend, TTSConfigMixin, AsyncTTSBackend
from podcastfy.core.character import Character


class ElevenLabsTTS(SyncTTSBackend, AsyncTTSBackend, TTSConfigMixin):
    name: str = "elevenlabs"

    def __init__(self, api_key: str = None, config_file: str = 'podcastfy/conversation_config.yaml'):
        TTSConfigMixin.__init__(self, config_file, name=self.name)
        self.api_key = api_key or os.getenv("ELEVENLABS_API_KEY")

    def text_to_speech(self, text: str, character: Character, output_path: Path) -> Path:
        config = self.tts_config_for_character(character)
        client = elevenlabs_client.ElevenLabs(api_key=self.api_key)  # # client could be reused
        content = client.generate(
            text=text,
            voice=config.voice,
            model=config.extra_args.get('model', self.get_default_config().get('model', 'default'))
        )
        with open(output_path, "wb") as out:
            for chunk in content:
                if chunk:
                    out.write(chunk)
        return output_path

    async def async_text_to_speech(self, text: str, character: Character, output_path: Path) -> Path:
        config = self.tts_config_for_character(character)
        client = elevenlabs_client.AsyncElevenLabs(api_key=self.api_key)
        content = await client.generate(
            text=text,
            voice=config.voice,
            model=config.extra_args.get('model', self.get_default_config().get('model', 'default'))
        )
        with open(output_path, "wb") as out:
            async for chunk in content:
                if chunk:
                    out.write(chunk)


class OpenAITTS(SyncTTSBackend, TTSConfigMixin):
    name: str = "openai"

    def __init__(self, api_key: str = None, config_file: str = 'podcastfy/conversation_config.yaml'):
        TTSConfigMixin.__init__(self, config_file, name=self.name)
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

    def text_to_speech(self, text: str, character: Character, output_path: Path) -> None:
        config = self.tts_config_for_character(character)

        print(f"OpenAI TTS: Converting text to speech for character {character.name} with voice {config.voice} \n text: {text}")
        model = config.extra_args.get('model', self.get_default_config().get('model', 'tts-1'))
        response = openai.audio.speech.create(
            model=model,
            voice=config.voice,
            input=text
        )
        with open(output_path, "wb") as file:
            file.write(response.content)



class EdgeTTS(AsyncTTSBackend, TTSConfigMixin):
    name: str = "edge"

    def __init__(self, config_file: str = 'podcastfy/conversation_config.yaml'):
        TTSConfigMixin.__init__(self, config_file, name=self.name)

    async def async_text_to_speech(self, text: str, character: Character, output_path: Path) -> None:
        config = self.tts_config_for_character(character)
        communicate = edge_tts.Communicate(text, config.voice)
        await communicate.save(str(output_path))

# register
SyncTTSBackend.register(ElevenLabsTTS)
AsyncTTSBackend.register(ElevenLabsTTS)
SyncTTSBackend.register(OpenAITTS)
AsyncTTSBackend.register(EdgeTTS)



# Example usage:
if __name__ == "__main__":
    from podcastfy.utils.config import load_config

    config = load_config()
    elevenlabs_tts = ElevenLabsTTS(config.ELEVENLABS_API_KEY)
    openai_tts = OpenAITTS(config.OPENAI_API_KEY)
    edge_tts = EdgeTTS()

    dummy_character1 = Character("character1", "host", {}, "A friendly podcast host")
    dummy_character2 = Character("character2", "guest", {}, "An expert guest")

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
