"""ModelsLab TTS provider implementation."""

import os
import time
from typing import Optional, List

import requests

from ..base import TTSProvider


# Voice name → ModelsLab voice_id mapping
# Full list: https://docs.modelslab.com/text-to-audio/realtime/tts
_VOICE_MAP = {
    "Bella":   1,
    "Antoni":  2,
    "Elli":    3,
    "Josh":    4,
    "Arnold":  5,
    "Adam":    6,
    "Sam":     7,
    "Rachel":  8,
    "Domi":    9,
    "Gigi":    10,
}

_API_URL   = "https://modelslab.com/api/v6/voice/text_to_speech"
_FETCH_URL = "https://modelslab.com/api/v6/voice/fetch/{}"


class ModelsLabTTS(TTSProvider):
    """ModelsLab Text-to-Speech provider.

    Supports 10 voices (Bella, Antoni, Elli, Josh, Arnold, Adam, Sam, Rachel,
    Domi, Gigi) with async generation polling.

    API docs: https://docs.modelslab.com/text-to-audio/realtime/tts
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "modelslab-tts-v1",
    ) -> None:
        """
        Initialise the ModelsLab TTS provider.

        Args:
            api_key: ModelsLab API key. Falls back to the ``MODELSLAB_API_KEY``
                     environment variable when *None*.
            model: Unused (kept for interface compatibility); ModelsLab TTS
                   does not expose a model selector at the API level.
        """
        self.api_key = api_key or os.environ.get("MODELSLAB_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ModelsLab API key must be provided or set via the "
                "MODELSLAB_API_KEY environment variable."
            )
        self.model = model

    # ------------------------------------------------------------------
    # TTSProvider interface
    # ------------------------------------------------------------------

    def generate_audio(
        self,
        text: str,
        voice: str,
        model: str,
        voice2: Optional[str] = None,
    ) -> bytes:
        """Generate audio using the ModelsLab TTS API.

        Args:
            text:   Text to synthesise (max 2 500 characters).
            voice:  Voice name — one of Bella, Antoni, Elli, Josh, Arnold,
                    Adam, Sam, Rachel, Domi, Gigi.
            model:  Ignored (retained for interface compatibility).
            voice2: Optional second voice name (unused; present for
                    interface compatibility with multi-speaker providers).

        Returns:
            Raw MP3 audio bytes.

        Raises:
            ValueError:   If *voice* is not a recognised ModelsLab voice.
            RuntimeError: If audio generation or download fails.
        """
        self.validate_parameters(text, voice, model)

        voice_id = _VOICE_MAP.get(voice)
        if voice_id is None:
            raise ValueError(
                f"Unknown ModelsLab voice '{voice}'. "
                f"Choose from: {', '.join(_VOICE_MAP)}"
            )

        # Enforce the 2 500-character limit
        if len(text) > 2500:
            text = text[:2500]

        payload = {
            "key":          self.api_key,
            "prompt":       text,
            "language":     "English",
            "voice_id":     voice_id,
            "audio_format": "mp3",
        }

        resp = requests.post(_API_URL, json=payload, timeout=(15, 60))
        resp.raise_for_status()
        data = resp.json()

        audio_url = self._resolve_audio_url(data)

        audio_resp = requests.get(audio_url, timeout=(10, 120))
        audio_resp.raise_for_status()
        return audio_resp.content

    def get_supported_tags(self) -> List[str]:
        """Return supported SSML tags (subset of common tags)."""
        return ["p", "s"]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_audio_url(self, data: dict) -> str:
        """Extract the final audio URL, polling if generation is async."""
        status = data.get("status")

        if status == "success":
            return self._extract_url(data)

        if status == "processing":
            request_id = data.get("id")
            if not request_id:
                raise RuntimeError(
                    "ModelsLab returned 'processing' but did not supply a request id."
                )
            return self._poll_for_url(request_id)

        raise RuntimeError(f"ModelsLab TTS API error: {data}")

    def _extract_url(self, data: dict) -> str:
        output = data.get("output") or data.get("output_url")
        if not output:
            raise RuntimeError(f"ModelsLab returned success but no audio URL: {data}")
        return output[0] if isinstance(output, list) else output

    def _poll_for_url(self, request_id: str, max_attempts: int = 60) -> str:
        fetch_url     = _FETCH_URL.format(request_id)
        fetch_payload = {"key": self.api_key}

        for _ in range(max_attempts):
            time.sleep(5)
            resp = requests.post(fetch_url, json=fetch_payload, timeout=(10, 30))
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") == "success":
                return self._extract_url(data)
            if data.get("status") == "processing":
                continue
            raise RuntimeError(f"ModelsLab fetch error: {data}")

        raise TimeoutError(
            f"ModelsLab TTS timed out after {max_attempts * 5}s for request {request_id}."
        )
