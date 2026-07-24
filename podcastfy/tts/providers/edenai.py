"""Eden AI TTS provider implementation."""

import base64
import os
from typing import List, Optional

import requests

from ..base import TTSProvider


class EdenAITTS(TTSProvider):
    """Eden AI Text-to-Speech provider.

    Eden AI is a gateway that exposes many text-to-speech engines (OpenAI,
    Google, Amazon, Microsoft, IBM, ElevenLabs and more) behind a single API
    and a single key. The `model` selects which engine to route the request to,
    so the list of available engines stays open as Eden AI adds providers.
    """

    API_URL = "https://api.edenai.run/v2/audio/text_to_speech"

    # Provider-specific SSML tags. Support varies by engine, so we keep this
    # conservative.
    PROVIDER_SSML_TAGS: List[str] = ['break', 'emphasis']

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "openai",
        language: str = "en",
    ):
        """
        Initialize Eden AI TTS provider.

        Args:
            api_key: Eden AI API key. If None, expects EDENAI_API_KEY env variable.
            model: Eden AI engine to route to (for example "openai", "google",
                "amazon", "microsoft"). Defaults to "openai".
            language: Language code passed to Eden AI (for example "en", "fr").
                Defaults to "en".
        """
        if not api_key:
            api_key = os.getenv("EDENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "Eden AI API key must be provided or set in the EDENAI_API_KEY "
                "environment variable"
            )
        self.api_key = api_key
        self.model = model
        self.language = language

    def get_supported_tags(self) -> List[str]:
        """Get all supported SSML tags including provider-specific ones."""
        return self.COMMON_SSML_TAGS + self.PROVIDER_SSML_TAGS

    def generate_audio(
        self, text: str, voice: str, model: str, voice2: str = None
    ) -> bytes:
        """Generate audio using the Eden AI text-to-speech API.

        A `voice` of "MALE" or "FEMALE" maps to Eden AI's gender option, which
        works across every engine. Any other value is treated as an engine
        specific voice id.
        """
        self.validate_parameters(text, voice, model)

        payload = {
            "providers": model,
            "language": self.language,
            "text": text,
        }
        if voice.upper() in ("MALE", "FEMALE"):
            payload["option"] = voice.upper()
        else:
            payload["settings"] = {model: voice}

        try:
            response = requests.post(
                self.API_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            result = response.json().get(model, {})
            if result.get("status") != "success":
                raise RuntimeError(
                    result.get("error", "Eden AI returned no audio")
                )
            return base64.b64decode(result["audio"])
        except Exception as e:
            raise RuntimeError(f"Failed to generate audio: {str(e)}") from e
