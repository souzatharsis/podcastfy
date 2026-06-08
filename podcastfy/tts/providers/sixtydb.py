"""60db (api.60db.ai) TTS provider implementation."""

import base64
import requests

from ..base import TTSProvider
from typing import List


class SixtyDbTTS(TTSProvider):
    """
    Text-to-Speech provider for 60db (https://60db.ai).

    Calls POST https://api.60db.ai/tts-synthesize and decodes the
    base64-wrapped audio payload into raw bytes so the rest of the
    podcastfy pipeline (pydub merge) treats the output identically
    to ElevenLabs / OpenAI providers.
    """

    API_URL = "https://api.60db.ai/tts-synthesize"

    # 60db caps a single synthesis request at this many characters.
    # Longer text must be chunked by the caller; we just guard here.
    MAX_TEXT_LENGTH = 5000

    def __init__(self, api_key: str = None, model: str = "60db-quality-v01"):
        """
        Initialize 60db TTS provider.

        Args:
            api_key (str): 60db API key (Bearer token from app.60db.ai
                → Settings → Developer → API Keys). Read from
                SIXTYDB_API_KEY env var if not supplied.
            model (str): Reserved for interface compatibility. 60db
                infers the active model from the voice_id, so this
                value is stored but not transmitted.
        """
        self.api_key = api_key
        self.model = model

    def generate_audio(
        self,
        text: str,
        voice: str,
        model: str,
        voice2: str = None,
    ) -> bytes:
        """
        Synthesize speech via the 60db REST API.

        Args:
            text: text to synthesize (<=5000 chars per 60db limit)
            voice: voice_id (UUID) or voice name configured in YAML
            model: ignored by this provider (see __init__ docstring)
            voice2: unused (single-speaker provider)

        Returns:
            Raw audio bytes in MP3 format.

        Raises:
            ValueError: empty/oversized text, missing voice, or missing API key.
            RuntimeError: 60db responded with success=false or unexpected payload.
            requests.HTTPError: non-2xx HTTP status from the 60db API.
        """
        self.validate_parameters(text, voice, model)
        if not self.api_key:
            raise ValueError(
                "60db API key missing. Set SIXTYDB_API_KEY or pass api_key explicitly."
            )
        if len(text) > self.MAX_TEXT_LENGTH:
            raise ValueError(
                f"Text exceeds 60db {self.MAX_TEXT_LENGTH}-char limit ({len(text)} given)."
            )

        # The 60db endpoint accepts either `voice_id` (UUID) or `voice` (name).
        # Treat anything with the canonical UUID dash pattern as a voice_id,
        # everything else as a friendly voice name.
        is_uuid_like = len(voice) == 36 and voice.count("-") == 4
        voice_field = "voice_id" if is_uuid_like else "voice"

        payload = {
            "text": text,
            voice_field: voice,
            "output_format": "mp3",
            "enhance": True,
        }

        response = requests.post(
            self.API_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=60,
        )
        response.raise_for_status()

        body = response.json()
        if not body.get("success") or "audio_base64" not in body:
            raise RuntimeError(
                f"60db TTS failed: {body.get('message', 'unknown error')}"
            )

        return base64.b64decode(body["audio_base64"])

    def get_supported_tags(self) -> List[str]:
        """
        Supported SSML tags. 60db docs do not enumerate SSML support, so we
        expose the conservative subset that ElevenLabs / common engines accept.
        """
        return ['lang', 'p', 's', 'sub']
