"""Edge TTS provider implementation."""

import edge_tts
import os
import tempfile
from typing import List
from ..base import TTSProvider

class EdgeTTS(TTSProvider):
    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize Edge TTS provider.
        
        Args:
            api_key (str): Not used for Edge TTS
            model (str): Model name to use
        """
        self.model = model or "default"  # Edge TTS doesn't use models, but we set it for consistency

    def generate_audio(self, text: str, voice: str, model: str, voice2: str = None) -> bytes:
        """Generate audio using Edge TTS."""
        import nest_asyncio
        import asyncio
        
        # Apply nest_asyncio to allow nested event loops
        nest_asyncio.apply()
        
        async def _generate():
            communicate = edge_tts.Communicate(text, voice)
            # Create a temporary file with proper context management
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp_file:
                temp_path = tmp_file.name
                
            try:
                # Save audio to temporary file
                await communicate.save(temp_path)
                # Read the audio data
                with open(temp_path, 'rb') as f:
                    return f.read()
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        # Use nest_asyncio to handle nested event loops
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_generate())
        
    def get_supported_tags(self) -> List[str]:
        """Get supported SSML tags."""
        return self.COMMON_SSML_TAGS