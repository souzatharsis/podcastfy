"""Google Cloud Text-to-Speech provider implementation."""

from google.cloud import texttospeech_v1beta1
from typing import List
from ..base import TTSProvider
import re
import logging

logger = logging.getLogger(__name__)

class GoogleMultispeakerTTS(TTSProvider):
    """Google Cloud Text-to-Speech provider with multi-speaker support."""
    
    def __init__(self, api_key: str = None, model: str = "en-US-Studio-MultiSpeaker"):
        """
        Initialize Google Cloud TTS provider.
        
        Args:
            api_key (str): Google Cloud API key
        """
        self.model = model
        try:
            self.client = texttospeech_v1beta1.TextToSpeechClient(
                client_options={'api_key': api_key} if api_key else None
            )
            self.ending_message = ""  # Required for split_qa method
        except Exception as e:
            logger.error(f"Failed to initialize Google TTS client: {str(e)}")
            raise
            
    def generate_audio(self, text: str, voice: str = "R", model: str = "en-US-Studio-MultiSpeaker", 
                       voice2: str = "S", ending_message: str = "") -> bytes:
        """
        Generate audio using Google Cloud TTS API with multi-speaker support.
        
        Args:
            text (str): Text to convert to speech (in Person1/Person2 format)
            voice (str): Voice ID for the current segment (R or S)
            model (str): Model name (must be 'en-US-Studio-MultiSpeaker')
            
        Returns:
            bytes: Audio data
            
        Raises:
            ValueError: If parameters are invalid
            RuntimeError: If audio generation fails
        """
        print(f"Generating audio with voice: {voice}, voice2: {voice2}, model: {model}")
        self.validate_parameters(text, voice, model)
          # Update model if different from default
        
        try:
            # Create multi-speaker markup
            multi_speaker_markup = texttospeech_v1beta1.MultiSpeakerMarkup()
            
            # Get Q&A pairs using the base class method
            qa_pairs = self.split_qa(text, ending_message, self.get_supported_tags())
            
            # Add turns for each Q&A pair
            for idx, (question, answer) in enumerate(qa_pairs, 1):
                print(f"question: {question}, answer: {answer}")
                # Add question turn
                q_turn = texttospeech_v1beta1.MultiSpeakerMarkup.Turn()
                q_turn.text = question.strip()
                q_turn.speaker = voice  # First speaker
                multi_speaker_markup.turns.append(q_turn)
                
                # Add answer turn
                a_turn = texttospeech_v1beta1.MultiSpeakerMarkup.Turn()
                a_turn.text = answer.strip()
                a_turn.speaker = voice2  # Second speaker
                multi_speaker_markup.turns.append(a_turn)
            
            # Create synthesis input with multi-speaker markup
            synthesis_input = texttospeech_v1beta1.SynthesisInput(
                multi_speaker_markup=multi_speaker_markup
            )
            
            # Set voice parameters - must use the multi-speaker model
            voice_params = texttospeech_v1beta1.VoiceSelectionParams(
                language_code="en-US",
                name=model  # Use the model attribute
            )
            
            # Set audio config
            audio_config = texttospeech_v1beta1.AudioConfig(
                audio_encoding=texttospeech_v1beta1.AudioEncoding.MP3
            )
            
            # Generate speech
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice_params,
                audio_config=audio_config
            )
            
            return response.audio_content
            
        except Exception as e:
            logger.error(f"Failed to generate audio: {str(e)}")
            raise RuntimeError(f"Failed to generate audio: {str(e)}") from e
    
    def get_supported_tags(self) -> List[str]:
        """Get supported SSML tags."""
        # Add any Google-specific SSML tags to the common ones
        return self.COMMON_SSML_TAGS
        
    def validate_parameters(self, text: str, voice: str, model: str) -> None:
        """
        Validate input parameters before generating audio.
        
        Args:
            text (str): Input text
            voice (str): Voice ID
            model (str): Model name
            
        Raises:
            ValueError: If parameters are invalid
        """
        super().validate_parameters(text, voice, model)
        
        # Additional validation for multi-speaker model
        if model != "en-US-Studio-MultiSpeaker":
            raise ValueError(
                "Google Multi-speaker TTS requires model='en-US-Studio-MultiSpeaker'"
            )