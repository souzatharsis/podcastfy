from typing import Dict, Any

from pydantic import BaseModel


class VoiceConfig(BaseModel):
    voice: str
    extra_args: Dict[str, Any] = {}


class TTSConfig(VoiceConfig):
    backend: str
