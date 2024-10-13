from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any
from podcastfy.character import Character

class TTSBackend(ABC):
    @abstractmethod
    def text_to_speech(self, text: str, character: Character) -> Path:
        """
        Convert text to speech.

        Args:
            text (str): The text to convert to speech.
            character (Character): The character for which to generate speech.

        Returns:
            Path: Path to the generated audio file.
        """
        pass

class ElevenLabsTTS(TTSBackend):
    def __init__(self, api_key: str, config: Dict[str, Any]):
        self.api_key = api_key
        self.config = config

    def text_to_speech(self, text: str, character: Character) -> Path:
        # Placeholder for ElevenLabs TTS implementation
        voice = character.get_tts_args('elevenlabs').get('voice', self.config['default_voice'])
        
        print(f"ElevenLabs TTS: Converting text to speech for character {character.name} with voice {voice}")
        
        # In a real implementation, this would call the ElevenLabs API and return the path to the generated audio file
        return Path(f"/tmp/{character.name}_audio.mp3")

class OpenAITTS(TTSBackend):
    def __init__(self, api_key: str, config: Dict[str, Any]):
        self.api_key = api_key
        self.config = config

    def text_to_speech(self, text: str, character: Character) -> Path:
        # Placeholder for OpenAI TTS implementation
        voice = character.get_tts_args('openai').get('voice', self.config['default_voice'])
        
        print(f"OpenAI TTS: Converting text to speech for character {character.name} with voice {voice}")
        
        # In a real implementation, this would call the OpenAI API and return the path to the generated audio file
        return Path(f"/tmp/{character.name}_audio.mp3")

# Example usage:
if __name__ == "__main__":
    from podcastfy.utils.config import load_config
    
    config = load_config()
    elevenlabs_tts = ElevenLabsTTS(config.ELEVENLABS_API_KEY, config.get('text_to_speech', {}).get('elevenlabs', {}))
    openai_tts = OpenAITTS(config.OPENAI_API_KEY, config.get('text_to_speech', {}).get('openai', {}))
    
    dummy_character = Character("John", "host", {
        'elevenlabs': {'voice': 'en-US-JohnNeural'},
        'openai': {'voice': 'en-US-Neural2-C'}
    }, "A friendly podcast host")
    
    elevenlabs_tts.text_to_speech("Hello, welcome to the podcast!", dummy_character)
