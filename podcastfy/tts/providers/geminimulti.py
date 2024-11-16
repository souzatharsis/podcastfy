"""Google Cloud Text-to-Speech provider implementation."""

from google.cloud import texttospeech_v1beta1
from typing import List
from ..base import TTSProvider
import re
import logging
from io import BytesIO
from pydub import AudioSegment

logger = logging.getLogger(__name__)

class GeminiMultiTTS(TTSProvider):
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
            logger.info("Successfully initialized GeminiMultiTTS client")
        except Exception as e:
            logger.error(f"Failed to initialize GeminiMultiTTS client: {str(e)}")
            raise
            
    def chunk_text(self, text: str, max_bytes: int = 1300) -> List[str]:
        """
        Split text into chunks that fit within Google TTS byte limit while preserving speaker tags.
        
        Args:
            text (str): Input text with Person1/Person2 tags
            max_bytes (int): Maximum bytes per chunk
            
        Returns:
            List[str]: List of text chunks with proper speaker tags preserved
        """
        logger.debug(f"Starting chunk_text with text length: {len(text)} bytes")
        
        # Split text into tagged sections, preserving both Person1 and Person2 tags
        pattern = r'(<Person[12]>.*?</Person[12]>)'
        sections = re.split(pattern, text, flags=re.DOTALL)
        sections = [s.strip() for s in sections if s.strip()]
        logger.debug(f"Split text into {len(sections)} sections")
        
        chunks = []
        current_chunk = ""
        
        for section in sections:
            # Extract speaker tag and content if this is a tagged section
            tag_match = re.match(r'<(Person[12])>(.*?)</Person[12]>', section, flags=re.DOTALL)
            
            if tag_match:
                speaker_tag = tag_match.group(1)  # Will be either Person1 or Person2
                content = tag_match.group(2).strip()
                
                # Test if adding this entire section would exceed limit
                test_chunk = current_chunk
                if current_chunk:
                    test_chunk += f"<{speaker_tag}>{content}</{speaker_tag}>"
                else:
                    test_chunk = f"<{speaker_tag}>{content}</{speaker_tag}>"
                    
                if len(test_chunk.encode('utf-8')) > max_bytes and current_chunk:
                    # Store current chunk and start new one
                    chunks.append(current_chunk)
                    current_chunk = f"<{speaker_tag}>{content}</{speaker_tag}>"
                else:
                    # Add to current chunk
                    current_chunk = test_chunk
        
        # Add final chunk if it exists
        if current_chunk:
            chunks.append(current_chunk)
            
        logger.info(f"Created {len(chunks)} chunks from input text")
        return chunks

    def split_turn_text(self, text: str, max_chars: int = 500) -> List[str]:
        """
        Split turn text into smaller chunks at sentence boundaries.
        
        Args:
            text (str): Text content of a single turn
            max_chars (int): Maximum characters per chunk
            
        Returns:
            List[str]: List of text chunks
        """
        #print(f"### TEXT: {text}" )
        #print(f"### LENGTH: {len(text)}")
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        sentences = re.split(r'([.!?]+(?:\s+|$))', text)
        sentences = [s for s in sentences if s]
        
        current_chunk = ""
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            separator = sentences[i + 1] if i + 1 < len(sentences) else ""
            complete_sentence = sentence + separator
            
            if len(current_chunk) + len(complete_sentence) > max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = complete_sentence
                else:
                    # If a single sentence is too long, split at word boundaries
                    words = complete_sentence.split()
                    temp_chunk = ""
                    for word in words:
                        if len(temp_chunk) + len(word) + 1 > max_chars:
                            chunks.append(temp_chunk.strip())
                            temp_chunk = word
                        else:
                            temp_chunk += " " + word if temp_chunk else word
                    current_chunk = temp_chunk
            else:
                current_chunk += complete_sentence
                
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks

    def merge_audio(self, audio_chunks: List[bytes]) -> bytes:
        """
        Merge multiple MP3 audio chunks into a single audio file.
        
        Args:
            audio_chunks (List[bytes]): List of MP3 audio data
            
        Returns:
            bytes: Combined MP3 audio data
        """
        if not audio_chunks:
            return b""
        
        if len(audio_chunks) == 1:
            return audio_chunks[0]
        
        try:
            # Initialize combined audio with first chunk
            combined = None
            valid_chunks = []
            
            for i, chunk in enumerate(audio_chunks):
                try:
                    # Ensure chunk is not empty
                    if not chunk or len(chunk) == 0:
                        logger.warning(f"Skipping empty chunk {i}")
                        continue
                    
                    # Save chunk to temporary file for ffmpeg to process
                    temp_file = f"temp_chunk_{i}.mp3"
                    with open(temp_file, "wb") as f:
                        f.write(chunk)
                    
                    # Create audio segment from temp file
                    try:
                        segment = AudioSegment.from_file(temp_file, format="mp3")
                        if len(segment) > 0:
                            valid_chunks.append(segment)
                            logger.debug(f"Successfully processed chunk {i}")
                        else:
                            logger.warning(f"Zero-length segment in chunk {i}")
                    except Exception as e:
                        logger.error(f"Error processing chunk {i}: {str(e)}")
                    
                    # Clean up temp file
                    import os
                    try:
                        os.remove(temp_file)
                    except Exception as e:
                        logger.warning(f"Failed to remove temp file {temp_file}: {str(e)}")
                    
                except Exception as e:
                    logger.error(f"Error handling chunk {i}: {str(e)}")
                    continue
            
            if not valid_chunks:
                raise RuntimeError("No valid audio chunks to merge")
            
            # Merge valid chunks
            combined = valid_chunks[0]
            for segment in valid_chunks[1:]:
                combined = combined + segment
            
            # Export with specific parameters
            output = BytesIO()
            combined.export(
                output,
                format="mp3",
                codec="libmp3lame",
                bitrate="320k"
            )
            
            result = output.getvalue()
            if len(result) == 0:
                raise RuntimeError("Export produced empty output")
            
            return result
            
        except Exception as e:
            logger.error(f"Audio merge failed: {str(e)}", exc_info=True)
            # If merging fails, return the first valid chunk as fallback
            if audio_chunks:
                return audio_chunks[0]
            raise RuntimeError(f"Failed to merge audio chunks and no valid fallback found: {str(e)}")

    def generate_audio(self, text: str, voice: str = "R", model: str = "en-US-Studio-MultiSpeaker", 
                       voice2: str = "S", ending_message: str = ""):
        """
        Generate audio using Google Cloud TTS API with multi-speaker support.
        Handles text longer than 5000 bytes by chunking and merging.
        """
        logger.info(f"Starting audio generation for text of length: {len(text)}")
        logger.debug(f"Parameters: voice={voice}, voice2={voice2}, model={model}")
        #print("######################### TEXT #########################")
        #print(text)
        #print("######################### END TEXT #########################")
        try:
            # Split text into chunks if needed
            text_chunks = self.chunk_text(text)
            logger.info(f"#########################33 Text split into {len(text_chunks)} chunks")
            audio_chunks = []
            #print(text_chunks[0])
            
            # Process each chunk
            for i, chunk in enumerate(text_chunks, 1):
                logger.debug(f"Processing chunk {i}/{len(text_chunks)}")
                # Create multi-speaker markup
                multi_speaker_markup = texttospeech_v1beta1.MultiSpeakerMarkup()
                #print("######################### CHUNK #########################")
                #print(chunk)
                # Get Q&A pairs for this chunk
                qa_pairs = self.split_qa(chunk, "", self.get_supported_tags())
                logger.debug(f"Found {len(qa_pairs)} Q&A pairs in chunk {i}")
                #print("######################### QA PAIRS #########################")
                #print(qa_pairs)
                # Add turns for each Q&A pair
                for j, (question, answer) in enumerate(qa_pairs, 1):
                    logger.debug(f"Processing Q&A pair {j}/{len(qa_pairs)}")
                    
                    # Split question into smaller chunks if needed
                    question_chunks = self.split_turn_text(question.strip())
                    logger.debug(f"Question split into {len(question_chunks)} chunks")
                    logger.debug(f"######################### Question chunks: {question_chunks}")
                    for q_chunk in question_chunks:
                        logger.debug(f"Adding question turn: '{q_chunk[:50]}...' (length: {len(q_chunk)})")
                        q_turn = texttospeech_v1beta1.MultiSpeakerMarkup.Turn()
                        q_turn.text = q_chunk
                        q_turn.speaker = voice
                        multi_speaker_markup.turns.append(q_turn)
                    
                    # Split answer into smaller chunks if needed
                    if answer:
                        answer_chunks = self.split_turn_text(answer.strip())
                        logger.debug(f"Answer split into {len(answer_chunks)} chunks")
                        logger.debug(f"######################### Answer chunks: {answer_chunks}")
                        for a_chunk in answer_chunks:
                            logger.debug(f"Adding answer turn: '{a_chunk[:50]}...' (length: {len(a_chunk)})")
                            a_turn = texttospeech_v1beta1.MultiSpeakerMarkup.Turn()
                            a_turn.text = a_chunk
                            a_turn.speaker = voice2
                            multi_speaker_markup.turns.append(a_turn)
                
                logger.debug(f"Created markup with {len(multi_speaker_markup.turns)} turns")
                
                # Create synthesis input with multi-speaker markup
                synthesis_input = texttospeech_v1beta1.SynthesisInput(
                    multi_speaker_markup=multi_speaker_markup
                )
                
                logger.debug("Calling synthesize_speech API")
                # Set voice parameters
                voice_params = texttospeech_v1beta1.VoiceSelectionParams(
                    language_code="en-US",
                    name=model
                )
                
                # Set audio config
                audio_config = texttospeech_v1beta1.AudioConfig(
                    audio_encoding=texttospeech_v1beta1.AudioEncoding.MP3,
                    #sample_rate_hertz=44100,  # Specify sample rate
                    #effects_profile_id=['headphone-class-device'],  # Optimize for headphones
                    #speaking_rate=1.0,  # Normal speaking rate
                )
                
                # Generate speech for this chunk
                response = self.client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice_params,
                    audio_config=audio_config
                )

                audio_chunks.append(response.audio_content)
            #print(f"#### Audio chunks: {audio_chunks}")
            #print(f"#### Audio chunks length: {len(audio_chunks)}")
            return audio_chunks
        
            
        except Exception as e:
            logger.error(f"Failed to generate audio: {str(e)}", exc_info=True)
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