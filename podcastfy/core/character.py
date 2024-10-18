from typing import Dict, Optional

from podcastfy.core.tts_configs import TTSConfig


class Character:
    """Represents a character in the podcast."""

    def __init__(self, name: str, role: str, tts_configs: Dict[str, TTSConfig] = {},
                 default_description_for_llm: str = ""):
        self.name = name
        self.role = role
        self.tts_configs = tts_configs
        self.default_description_for_llm = default_description_for_llm
        self.preferred_tts = next(iter(tts_configs.keys()), None)  # Set first TTS as default, can be None

    def set_preferred_tts(self, tts_name: str):
        if tts_name not in self.tts_configs:
            raise ValueError(f"TTS backend '{tts_name}' not configured for this character")
        self.preferred_tts = tts_name

    def to_prompt(self) -> str:
        """Convert the character information to a prompt for the LLM."""
        #TODO: could be improved by adding more information than roles
        return f"Character: {self.name}\nRole: {self.role}\n{self.default_description_for_llm.format(name=self.name)}"

    def get_tts_args(self, tts_name: Optional[str] = None) -> TTSConfig:
        """Get the TTS arguments for this character."""
        tts_name = tts_name or self.preferred_tts
        return self.tts_configs[tts_name]
