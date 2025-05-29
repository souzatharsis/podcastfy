"""Google Gemini TTS provider implementation using the new Gemini API."""

from google import genai
from google.genai import types
from typing import List
from ..base import TTSProvider
import re
import logging
from io import BytesIO
from pydub import AudioSegment
import base64
import wave

logger = logging.getLogger(__name__)

class GeminiNewTTS(TTSProvider):
    """Google Gemini TTS provider using the new Gemini API with multi-speaker support."""
    
    def __init__(self, api_key: str = None, model: str = "gemini-2.5-flash-preview-tts"):
        """
        Initialize Google Gemini TTS provider.
        
        Args:
            api_key (str): Google Gemini API key
            model (str): Model name to use (default: gemini-2.5-flash-preview-tts)
        """
        logger.info(f"🏗️ Initializing GeminiNewTTS with model: {model}")
        logger.debug(f"API key provided: {'Yes' if api_key else 'No'}")
        
        self.model = model
        try:
            self.client = genai.Client(api_key=api_key)
            logger.info("✅ Successfully initialized GeminiNewTTS client")
        except Exception as e:
            logger.error(f"❌ Failed to initialize GeminiNewTTS client: {str(e)}")
            raise
            
    def chunk_text(self, text: str, max_chars: int = 30000) -> List[str]:
        """
        Split text into chunks that fit within Gemini API limits while preserving speaker tags.
        
        Args:
            text (str): Input text with Person1/Person2 tags
            max_chars (int): Maximum characters per chunk
            
        Returns:
            List[str]: List of text chunks with proper speaker tags preserved
        """
        logger.info(f"📝 Starting chunk_text with text length: {len(text)} characters, max_chars: {max_chars}")
        logger.debug(f"Input text preview: {text[:100]}...")
        
        # For shorter texts, return as single chunk
        if len(text) <= max_chars:
            logger.info(f"✅ Text is short enough, returning single chunk")
            return [text]
        
        # Split text into tagged sections, preserving both Person1 and Person2 tags
        pattern = r'(<Person[12]>.*?</Person[12]>)'
        sections = re.split(pattern, text, flags=re.DOTALL)
        sections = [s.strip() for s in sections if s.strip()]
        logger.info(f"🔪 Split text into {len(sections)} sections using regex pattern")
        
        chunks = []
        current_chunk = ""
        
        for i, section in enumerate(sections):
            logger.debug(f"Processing section {i+1}/{len(sections)}: {section[:50]}...")
            
            # Extract speaker tag and content if this is a tagged section
            tag_match = re.match(r'<(Person[12])>(.*?)</Person[12]>', section, flags=re.DOTALL)
            
            if tag_match:
                speaker_tag = tag_match.group(1)  # Will be either Person1 or Person2
                content = tag_match.group(2).strip()
                logger.debug(f"Found {speaker_tag} section with {len(content)} characters")
                
                # Test if adding this entire section would exceed limit
                test_chunk = current_chunk
                if current_chunk:
                    test_chunk += f" <{speaker_tag}>{content}</{speaker_tag}>"
                else:
                    test_chunk = f"<{speaker_tag}>{content}</{speaker_tag}>"
                    
                if len(test_chunk) > max_chars and current_chunk:
                    # Store current chunk and start new one
                    logger.debug(f"Chunk size would be {len(test_chunk)}, creating new chunk")
                    chunks.append(current_chunk)
                    current_chunk = f"<{speaker_tag}>{content}</{speaker_tag}>"
                else:
                    # Add to current chunk
                    current_chunk = test_chunk
                    logger.debug(f"Added to current chunk, new size: {len(current_chunk)}")
            else:
                logger.debug(f"Non-tagged section: {section[:30]}...")
        
        # Add final chunk if it exists
        if current_chunk:
            chunks.append(current_chunk)
            
        logger.info(f"✅ Created {len(chunks)} chunks from input text")
        for i, chunk in enumerate(chunks):
            logger.debug(f"Chunk {i+1} length: {len(chunk)} characters")
        return chunks

    def convert_to_gemini_format(self, text: str, voice1_name: str = "Host", voice2_name: str = "Guest") -> str:
        """
        Convert Person1/Person2 format to Gemini's expected format.
        
        Args:
            text (str): Text with Person1/Person2 tags
            voice1_name (str): Name for Person1 speaker
            voice2_name (str): Name for Person2 speaker
            
        Returns:
            str: Text formatted for Gemini multi-speaker TTS
        """
        logger.info(f"🔄 Converting text format: Person1→{voice1_name}, Person2→{voice2_name}")
        logger.debug(f"Input text length: {len(text)} characters")
        logger.debug(f"Input text preview: {text[:150]}...")
        
        # Replace Person1 with voice1_name and Person2 with voice2_name
        converted = text.replace('<Person1>', f'<{voice1_name}>').replace('</Person1>', f'</{voice1_name}>')
        converted = converted.replace('<Person2>', f'<{voice2_name}>').replace('</Person2>', f'</{voice2_name}>')
        
        # Add TTS instruction at the beginning
        instruction = f"TTS the following conversation between {voice1_name} and {voice2_name}:\n"
        result = instruction + converted
        
        logger.info(f"✅ Text conversion completed")
        logger.debug(f"Final text length: {len(result)} characters")
        logger.debug(f"Final text preview: {result[:200]}...")
        
        return result

    def merge_audio(self, audio_chunks: List[bytes]) -> bytes:
        """
        Merge multiple audio chunks into a single audio file.
        
        Args:
            audio_chunks (List[bytes]): List of audio data (MP3 format)
            
        Returns:
            bytes: Combined audio data in MP3 format
        """
        logger.info(f"🔗 === STARTING AUDIO MERGE ===")
        logger.info(f"📊 Merging {len(audio_chunks)} audio chunks")
        
        if not audio_chunks:
            logger.warning(f"⚠️ No audio chunks provided, returning empty bytes")
            return b""
        
        if len(audio_chunks) == 1:
            logger.info(f"✅ Single chunk provided, returning directly (size: {len(audio_chunks[0])} bytes)")
            return audio_chunks[0]
        
        # Log chunk sizes
        for i, chunk in enumerate(audio_chunks):
            logger.debug(f"Chunk {i+1} size: {len(chunk)} bytes")
        
        try:
            # Initialize combined audio with first chunk
            combined = None
            valid_chunks = []
            
            for i, chunk in enumerate(audio_chunks):
                logger.debug(f"🔄 Processing audio chunk {i+1}/{len(audio_chunks)}")
                try:
                    # Ensure chunk is not empty
                    if not chunk or len(chunk) == 0:
                        logger.warning(f"⚠️ Skipping empty chunk {i+1}")
                        continue
                    
                    # Create audio segment from raw MP3 data
                    try:
                        segment = AudioSegment.from_mp3(BytesIO(chunk))
                        if len(segment) > 0:
                            valid_chunks.append(segment)
                            logger.info(f"✅ Successfully processed chunk {i+1}: {len(segment)}ms duration")
                        else:
                            logger.warning(f"⚠️ Zero-length segment in chunk {i+1}")
                    except Exception as e:
                        logger.error(f"❌ Error processing chunk {i+1}: {str(e)}")
                    
                except Exception as e:
                    logger.error(f"❌ Error handling chunk {i+1}: {str(e)}")
                    continue
            
            if not valid_chunks:
                logger.error(f"💥 No valid audio chunks to merge!")
                raise RuntimeError("No valid audio chunks to merge")
            
            logger.info(f"🎵 Merging {len(valid_chunks)} valid audio segments")
            
            # Merge valid chunks
            combined = valid_chunks[0]
            logger.debug(f"Base segment: {len(combined)}ms")
            
            for i, segment in enumerate(valid_chunks[1:], 1):
                logger.debug(f"Adding segment {i+1}: {len(segment)}ms")
                combined = combined + segment
            
            total_duration = len(combined)
            logger.info(f"🎶 Combined audio duration: {total_duration}ms")
            
            # Export to MP3 bytes
            logger.debug(f"🔄 Exporting to MP3 format...")
            output = BytesIO()
            combined.export(
                output,
                format="mp3",
                codec="libmp3lame",
                bitrate="320k"
            )
            
            result = output.getvalue()
            if len(result) == 0:
                logger.error(f"💥 Export produced empty output!")
                raise RuntimeError("Export produced empty output")
            
            logger.info(f"✅ === AUDIO MERGE COMPLETED ===")
            logger.info(f"📊 Final merged audio size: {len(result)} bytes")
            return result
            
        except Exception as e:
            logger.error(f"💥 === AUDIO MERGE FAILED ===")
            logger.error(f"❌ Audio merge failed: {str(e)}", exc_info=True)
            # If merging fails, return the first valid chunk as fallback
            if audio_chunks:
                logger.warning(f"🔄 Returning first chunk as fallback (size: {len(audio_chunks[0])} bytes)")
                return audio_chunks[0]
            raise RuntimeError(f"Failed to merge audio chunks and no valid fallback found: {str(e)}")

    def generate_single_speaker_audio(self, text: str, voice_name: str = "Kore") -> bytes:
        """
        Generate single-speaker audio using Gemini API.
        
        Args:
            text (str): Text to convert to speech
            voice_name (str): Voice name (default: Kore)
            
        Returns:
            bytes: Audio data in MP3 format
        """
        try:
            logger.info(f"🗣️ === GENERATING SINGLE-SPEAKER AUDIO ===")
            logger.info(f"📊 Parameters:")
            logger.info(f"   - Voice: {voice_name}")
            logger.info(f"   - Text length: {len(text)} characters")
            logger.info(f"   - Model: {self.model}")
            logger.debug(f"📄 Text content: {text[:150]}...")
            
            logger.debug(f"🚀 Calling Gemini API...")
            response = self.client.models.generate_content(
                model=self.model,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=voice_name
                            )
                        )
                    )
                )
            )
            logger.info(f"✅ API call completed successfully")
            
            # Inspect the response structure
            logger.debug(f"🔍 Response structure inspection:")
            logger.debug(f"   - Candidates count: {len(response.candidates)}")
            logger.debug(f"   - Parts count: {len(response.candidates[0].content.parts)}")
            logger.debug(f"   - Part type: {type(response.candidates[0].content.parts[0])}")
            
            # Check if inline_data exists and its structure
            part = response.candidates[0].content.parts[0]
            if hasattr(part, 'inline_data'):
                logger.debug(f"   - Inline data exists: True")
                logger.debug(f"   - Inline data type: {type(part.inline_data)}")
                if hasattr(part.inline_data, 'mime_type'):
                    logger.debug(f"   - MIME type: {part.inline_data.mime_type}")
                if hasattr(part.inline_data, 'data'):
                    logger.debug(f"   - Data field exists: True, type: {type(part.inline_data.data)}")
                else:
                    logger.error(f"❌ No 'data' field in inline_data!")
            else:
                logger.error(f"❌ No 'inline_data' field in response part!")
                logger.debug(f"   - Available attributes: {dir(part)}")
            
            # Extract audio data from response
            audio_data = response.candidates[0].content.parts[0].inline_data.data
            logger.info(f"📦 Received audio data type: {type(audio_data)}")
            
            # Check if we have binary data or base64 text
            if isinstance(audio_data, bytes):
                logger.info(f"🎵 Received binary audio data directly: {len(audio_data)} bytes")
                pcm_data = audio_data
                logger.info(f"✅ Using binary data directly as PCM")
                
            elif isinstance(audio_data, str):
                logger.info(f"📝 Received base64 audio data: {len(audio_data)} characters")
                logger.info(f"🔍 Base64 data preview (first 200 chars): {audio_data[:200]}")
                logger.info(f"🔍 Base64 data preview (last 200 chars): {audio_data[-200:]}")
                
                # Check for common base64 issues
                invalid_chars = [c for c in audio_data[:1000] if c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=']
                if invalid_chars:
                    logger.error(f"❌ Found invalid base64 characters in first 1000 chars: {set(invalid_chars)}")
                else:
                    logger.info(f"✅ First 1000 characters appear to be valid base64")
                
                # Check for unusual patterns
                if '\n' in audio_data[:1000]:
                    logger.warning(f"⚠️ Found newlines in base64 data")
                if ' ' in audio_data[:1000]:
                    logger.warning(f"⚠️ Found spaces in base64 data")
                if '\r' in audio_data[:1000]:
                    logger.warning(f"⚠️ Found carriage returns in base64 data")
                
                # Convert base64 to bytes
                try:
                    pcm_data = base64.b64decode(audio_data)
                    logger.info(f"🔄 Decoded PCM data length: {len(pcm_data)} bytes")
                    
                    # Calculate expected vs actual ratio
                    expected_size = len(audio_data) * 3 / 4  # Base64 to binary ratio
                    actual_size = len(pcm_data)
                    ratio = actual_size / expected_size if expected_size > 0 else 0
                    logger.info(f"📊 Decode ratio: {actual_size}/{expected_size:.0f} = {ratio:.3f} (should be ~1.0)")
                    
                    if ratio < 0.5:
                        logger.error(f"💥 CRITICAL: Base64 decode ratio is too low! Expected ~{expected_size:.0f} bytes, got {actual_size}")
                        
                        # Try cleaning the base64 data and decoding again
                        logger.info(f"🧹 Attempting to clean base64 data and retry decode...")
                        
                        # Remove whitespace and invalid characters
                        cleaned_audio_data = ''.join(c for c in audio_data if c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
                        logger.info(f"🧹 Cleaned base64 length: {len(cleaned_audio_data)} characters (removed {len(audio_data) - len(cleaned_audio_data)} chars)")
                        
                        # Try decoding the cleaned data
                        try:
                            cleaned_pcm_data = base64.b64decode(cleaned_audio_data)
                            logger.info(f"✅ Cleaned decode successful: {len(cleaned_pcm_data)} bytes")
                            
                            # Update the data to use cleaned version
                            pcm_data = cleaned_pcm_data
                            actual_size = len(pcm_data)
                            ratio = actual_size / expected_size if expected_size > 0 else 0
                            logger.info(f"📊 Cleaned decode ratio: {actual_size}/{expected_size:.0f} = {ratio:.3f}")
                            
                        except Exception as clean_e:
                            logger.error(f"❌ Cleaned base64 decode also failed: {str(clean_e)}")
                            # Continue with original data
                            pass
                        
                except Exception as e:
                    logger.error(f"❌ Base64 decode failed: {str(e)}")
                    raise
                
            else:
                logger.error(f"❌ Unknown audio data type: {type(audio_data)}")
                raise RuntimeError(f"Unexpected audio data type: {type(audio_data)}")
            
            # Log the PCM data info
            logger.info(f"🎵 PCM data analysis:")
            logger.info(f"   - Size: {len(pcm_data)} bytes")
            if len(pcm_data) >= 16:
                logger.info(f"   - First 16 bytes: {pcm_data[:16].hex()}")
                logger.info(f"   - Last 16 bytes: {pcm_data[-16:].hex()}")
            
            # Check if the decoded data is already in a known audio format (for successful decode)
            if len(pcm_data) >= 4:
                header = pcm_data[:4]
                logger.info(f"🔍 Data header bytes: {header.hex()}")
                
                if header == b'RIFF':
                    logger.info(f"🎵 Detected WAV format in decoded data!")
                    wav_segment = AudioSegment.from_wav(BytesIO(pcm_data))
                    logger.info(f"🎶 Direct WAV AudioSegment: {len(wav_segment)}ms duration")
                    
                    mp3_output = BytesIO()
                    wav_segment.export(mp3_output, format="mp3", codec="libmp3lame", bitrate="320k")
                    result = mp3_output.getvalue()
                    logger.info(f"✅ Direct WAV to MP3 conversion completed: {len(result)} bytes")
                    return result
                    
                elif header[:3] == b'ID3' or header[:2] == b'\xff\xfb':
                    logger.info(f"🎵 Detected MP3 format in decoded data!")
                    logger.info(f"✅ Returning MP3 data directly: {len(pcm_data)} bytes")
                    return pcm_data
                else:
                    logger.info(f"🔍 Unknown format header, treating as raw PCM")
            else:
                logger.warning(f"⚠️ Data too short for format detection: {len(pcm_data)} bytes")
            
            # If we get here, treat as PCM data
            logger.info(f"🎵 Treating decoded data as raw PCM format")
            
            # Convert PCM to MP3 format
            logger.debug(f"🎵 Converting PCM to MP3...")
            mp3_data = self.pcm_to_mp3(pcm_data)
            logger.info(f"✅ Converted MP3 data length: {len(mp3_data)} bytes")
            
            logger.info(f"🎉 === SINGLE-SPEAKER AUDIO GENERATION COMPLETED ===")
            return mp3_data
            
        except Exception as e:
            logger.error(f"💥 === SINGLE-SPEAKER AUDIO GENERATION FAILED ===")
            logger.error(f"❌ Single speaker audio generation failed: {str(e)}")
            raise RuntimeError(f"Failed to generate single speaker audio: {str(e)}") from e

    def generate_multi_speaker_audio(self, text: str, voice1_name: str = "Kore", voice2_name: str = "Puck", 
                                   speaker1_name: str = "Host", speaker2_name: str = "Guest") -> bytes:
        """
        Generate multi-speaker audio using Gemini API.
        
        Args:
            text (str): Text with speaker tags
            voice1_name (str): Voice for first speaker (default: Kore)
            voice2_name (str): Voice for second speaker (default: Puck)
            speaker1_name (str): Name for first speaker in conversation (default: Host)
            speaker2_name (str): Name for second speaker in conversation (default: Guest)
            
        Returns:
            bytes: Audio data in MP3 format
        """
        try:
            logger.info(f"🎭 === GENERATING MULTI-SPEAKER AUDIO ===")
            logger.info(f"📊 Parameters:")
            logger.info(f"   - Voice 1 ({speaker1_name}): {voice1_name}")
            logger.info(f"   - Voice 2 ({speaker2_name}): {voice2_name}")
            logger.info(f"   - Text length: {len(text)} characters")
            logger.info(f"   - Model: {self.model}")
            logger.debug(f"📄 Input text preview: {text[:150]}...")
            
            # Convert to Gemini format
            logger.debug(f"🔄 Converting text to Gemini format...")
            gemini_text = self.convert_to_gemini_format(text, speaker1_name, speaker2_name)
            logger.info(f"✅ Text conversion completed")
            
            logger.debug(f"🚀 Calling Gemini multi-speaker API...")
            
            response = self.client.models.generate_content(
                model=self.model,
                contents=gemini_text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                            speaker_voice_configs=[
                                types.SpeakerVoiceConfig(
                                    speaker=speaker1_name,
                                    voice_config=types.VoiceConfig(
                                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                            voice_name=voice1_name
                                        )
                                    )
                                ),
                                types.SpeakerVoiceConfig(
                                    speaker=speaker2_name,
                                    voice_config=types.VoiceConfig(
                                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                            voice_name=voice2_name
                                        )
                                    )
                                )
                            ]
                        )
                    )
                )
            )
            logger.info(f"✅ Multi-speaker API call completed successfully")
            
            # Inspect the response structure
            logger.debug(f"🔍 Response structure inspection:")
            logger.debug(f"   - Candidates count: {len(response.candidates)}")
            logger.debug(f"   - Parts count: {len(response.candidates[0].content.parts)}")
            logger.debug(f"   - Part type: {type(response.candidates[0].content.parts[0])}")
            
            # Check if inline_data exists and its structure
            part = response.candidates[0].content.parts[0]
            if hasattr(part, 'inline_data'):
                logger.debug(f"   - Inline data exists: True")
                logger.debug(f"   - Inline data type: {type(part.inline_data)}")
                if hasattr(part.inline_data, 'mime_type'):
                    logger.debug(f"   - MIME type: {part.inline_data.mime_type}")
                if hasattr(part.inline_data, 'data'):
                    logger.debug(f"   - Data field exists: True, type: {type(part.inline_data.data)}")
                else:
                    logger.error(f"❌ No 'data' field in inline_data!")
            else:
                logger.error(f"❌ No 'inline_data' field in response part!")
                logger.debug(f"   - Available attributes: {dir(part)}")
            
            # Extract audio data from response
            audio_data = response.candidates[0].content.parts[0].inline_data.data
            logger.info(f"📦 Received audio data type: {type(audio_data)}")
            
            # Check if we have binary data or base64 text
            if isinstance(audio_data, bytes):
                logger.info(f"🎵 Received binary audio data directly: {len(audio_data)} bytes")
                pcm_data = audio_data
                logger.info(f"✅ Using binary data directly as PCM")
                
            elif isinstance(audio_data, str):
                logger.info(f"📝 Received base64 audio data: {len(audio_data)} characters")
                logger.info(f"🔍 Base64 data preview (first 200 chars): {audio_data[:200]}")
                logger.info(f"🔍 Base64 data preview (last 200 chars): {audio_data[-200:]}")
                
                # Check for common base64 issues
                invalid_chars = [c for c in audio_data[:1000] if c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=']
                if invalid_chars:
                    logger.error(f"❌ Found invalid base64 characters in first 1000 chars: {set(invalid_chars)}")
                else:
                    logger.info(f"✅ First 1000 characters appear to be valid base64")
                
                # Check for unusual patterns
                if '\n' in audio_data[:1000]:
                    logger.warning(f"⚠️ Found newlines in base64 data")
                if ' ' in audio_data[:1000]:
                    logger.warning(f"⚠️ Found spaces in base64 data")
                if '\r' in audio_data[:1000]:
                    logger.warning(f"⚠️ Found carriage returns in base64 data")
                
                # Convert base64 to bytes
                try:
                    pcm_data = base64.b64decode(audio_data)
                    logger.info(f"🔄 Decoded PCM data length: {len(pcm_data)} bytes")
                    
                    # Calculate expected vs actual ratio
                    expected_size = len(audio_data) * 3 / 4  # Base64 to binary ratio
                    actual_size = len(pcm_data)
                    ratio = actual_size / expected_size if expected_size > 0 else 0
                    logger.info(f"📊 Decode ratio: {actual_size}/{expected_size:.0f} = {ratio:.3f} (should be ~1.0)")
                    
                    if ratio < 0.5:
                        logger.error(f"💥 CRITICAL: Base64 decode ratio is too low! Expected ~{expected_size:.0f} bytes, got {actual_size}")
                        
                        # Try cleaning the base64 data and decoding again
                        logger.info(f"🧹 Attempting to clean base64 data and retry decode...")
                        
                        # Remove whitespace and invalid characters
                        cleaned_audio_data = ''.join(c for c in audio_data if c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
                        logger.info(f"🧹 Cleaned base64 length: {len(cleaned_audio_data)} characters (removed {len(audio_data) - len(cleaned_audio_data)} chars)")
                        
                        # Try decoding the cleaned data
                        try:
                            cleaned_pcm_data = base64.b64decode(cleaned_audio_data)
                            logger.info(f"✅ Cleaned decode successful: {len(cleaned_pcm_data)} bytes")
                            
                            # Update the data to use cleaned version
                            pcm_data = cleaned_pcm_data
                            actual_size = len(pcm_data)
                            ratio = actual_size / expected_size if expected_size > 0 else 0
                            logger.info(f"📊 Cleaned decode ratio: {actual_size}/{expected_size:.0f} = {ratio:.3f}")
                            
                        except Exception as clean_e:
                            logger.error(f"❌ Cleaned base64 decode also failed: {str(clean_e)}")
                            # Continue with original data
                            pass
                        
                except Exception as e:
                    logger.error(f"❌ Base64 decode failed: {str(e)}")
                    raise
                
            else:
                logger.error(f"❌ Unknown audio data type: {type(audio_data)}")
                raise RuntimeError(f"Unexpected audio data type: {type(audio_data)}")
            
            # Log the PCM data info
            logger.info(f"🎵 PCM data analysis:")
            logger.info(f"   - Size: {len(pcm_data)} bytes")
            if len(pcm_data) >= 16:
                logger.info(f"   - First 16 bytes: {pcm_data[:16].hex()}")
                logger.info(f"   - Last 16 bytes: {pcm_data[-16:].hex()}")
            
            # Check if the decoded data is already in a known audio format (for successful decode)
            if len(pcm_data) >= 4:
                header = pcm_data[:4]
                logger.info(f"🔍 Data header bytes: {header.hex()}")
                
                if header == b'RIFF':
                    logger.info(f"🎵 Detected WAV format in decoded data!")
                    wav_segment = AudioSegment.from_wav(BytesIO(pcm_data))
                    logger.info(f"🎶 Direct WAV AudioSegment: {len(wav_segment)}ms duration")
                    
                    mp3_output = BytesIO()
                    wav_segment.export(mp3_output, format="mp3", codec="libmp3lame", bitrate="320k")
                    result = mp3_output.getvalue()
                    logger.info(f"✅ Direct WAV to MP3 conversion completed: {len(result)} bytes")
                    return result
                    
                elif header[:3] == b'ID3' or header[:2] == b'\xff\xfb':
                    logger.info(f"🎵 Detected MP3 format in decoded data!")
                    logger.info(f"✅ Returning MP3 data directly: {len(pcm_data)} bytes")
                    return pcm_data
                else:
                    logger.info(f"🔍 Unknown format header, treating as raw PCM")
            else:
                logger.warning(f"⚠️ Data too short for format detection: {len(pcm_data)} bytes")
            
            # If we get here, treat as PCM data
            logger.info(f"🎵 Treating decoded data as raw PCM format")
            
            # Convert PCM to MP3 format
            logger.debug(f"🎵 Converting PCM to MP3...")
            mp3_data = self.pcm_to_mp3(pcm_data)
            logger.info(f"✅ Converted MP3 data length: {len(mp3_data)} bytes")
            
            logger.info(f"🎉 === MULTI-SPEAKER AUDIO GENERATION COMPLETED ===")
            return mp3_data
            
        except Exception as e:
            logger.error(f"💥 === MULTI-SPEAKER AUDIO GENERATION FAILED ===")
            logger.error(f"❌ Multi-speaker audio generation failed: {str(e)}")
            raise RuntimeError(f"Failed to generate multi-speaker audio: {str(e)}") from e

    def pcm_to_mp3(self, pcm_data: bytes, channels: int = 1, sample_rate: int = 24000, sample_width: int = 2) -> bytes:
        """
        Convert PCM data to MP3 format.
        
        Args:
            pcm_data (bytes): Raw PCM audio data
            channels (int): Number of audio channels (default: 1)
            sample_rate (int): Sample rate in Hz (default: 24000)
            sample_width (int): Sample width in bytes (default: 2)
            
        Returns:
            bytes: MP3 formatted audio data
        """
        logger.info(f"🎵 === STARTING PCM TO MP3 CONVERSION ===")
        logger.info(f"📊 Audio parameters:")
        logger.info(f"   - PCM data size: {len(pcm_data)} bytes")
        logger.info(f"   - Channels: {channels}")
        logger.info(f"   - Sample rate: {sample_rate}Hz")
        logger.info(f"   - Sample width: {sample_width} bytes")
        
        # Calculate expected duration
        samples_per_second = sample_rate * channels * sample_width
        expected_duration_ms = (len(pcm_data) / samples_per_second) * 1000
        logger.info(f"📏 Expected audio duration: {expected_duration_ms:.1f}ms")
        
        # First convert PCM to WAV, then to MP3
        logger.debug(f"🔄 Step 1: Converting PCM to WAV format...")
        wav_output = BytesIO()
        
        with wave.open(wav_output, 'wb') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_data)
        
        # Convert WAV to MP3
        wav_data = wav_output.getvalue()
        logger.info(f"✅ Created WAV data: {len(wav_data)} bytes")
        
        logger.debug(f"🔄 Step 2: Loading WAV into AudioSegment...")
        wav_segment = AudioSegment.from_wav(BytesIO(wav_data))
        logger.info(f"🎶 AudioSegment created:")
        logger.info(f"   - Duration: {len(wav_segment)}ms")
        logger.info(f"   - Channels: {wav_segment.channels}")
        logger.info(f"   - Frame rate: {wav_segment.frame_rate}Hz")
        logger.info(f"   - Sample width: {wav_segment.sample_width} bytes")
        
        # Check if duration makes sense
        if len(wav_segment) < 10:
            logger.warning(f"⚠️ Very short audio duration: {len(wav_segment)}ms - this might be an issue!")
        
        logger.debug(f"🔄 Step 3: Exporting to MP3 format...")
        mp3_output = BytesIO()
        wav_segment.export(
            mp3_output,
            format="mp3",
            codec="libmp3lame",
            bitrate="320k"
        )
        
        result = mp3_output.getvalue()
        logger.info(f"✅ === PCM TO MP3 CONVERSION COMPLETED ===")
        logger.info(f"📊 Final MP3 data: {len(result)} bytes")
        
        if len(result) < 1000:
            logger.warning(f"⚠️ Very small MP3 file size: {len(result)} bytes - this might indicate an issue!")
        
        return result

    def generate_audio( self, text: str, voice: str = "Kore", model: str = None, 
                       voice2: str = "Puck", ending_message: str = "") -> bytes:
        """
        Generate audio using Google Gemini TTS API with multi-speaker support.
        Handles text longer than context limits by chunking and merging.
        
        Args:
            text (str): Text to convert to speech
            voice (str): Voice for first speaker (default: Kore)
            model (str): Model to use (optional, uses instance model if None)
            voice2 (str): Voice for second speaker (default: Puck)
            ending_message (str): Optional ending message
            
        Returns:
            bytes: Audio data in MP3 format (single chunk for compatibility with existing system)
        """
        # NEW HACK FOR SPEAKING STYLE
        prepend_text = "Say in a spooky Whisper: "
        text = prepend_text + text
        # NEW

        logger.info(f"🎵 === STARTING AUDIO GENERATION ===")
        logger.info(f"📊 Input parameters:")
        logger.info(f"   - Text length: {len(text)} characters")
        logger.info(f"   - Voice 1: {voice}")
        logger.info(f"   - Voice 2: {voice2}")
        logger.info(f"   - Model: {model or self.model}")
        logger.info(f"   - Ending message: '{ending_message}'")
        logger.debug(f"📄 Text preview: {text[:200]}...")
        
        # Use instance model if none provided
        if model is None:
            model = self.model
            logger.debug(f"Using instance model: {model}")
        
        try:
            # Check if text contains speaker tags for multi-speaker
            has_speaker_tags = '<Person1>' in text or '<Person2>' in text
            logger.info(f"🔍 Speaker tags detected: {has_speaker_tags}")
            
            if has_speaker_tags:
                logger.info(f"🎭 Using MULTI-SPEAKER mode")
                
                # Add ending message if needed
                if ending_message and not text.strip().endswith('</Person2>'):
                    old_length = len(text)
                    text = text.rstrip() + f" <Person2>{ending_message}</Person2>"
                    logger.info(f"📝 Added ending message, text length: {old_length} → {len(text)}")
                
                # Split text into chunks if needed
                text_chunks = self.chunk_text(text)
                logger.info(f"📦 Text split into {len(text_chunks)} chunks for multi-speaker")
                
                audio_chunks = []
                
                # Process each chunk
                for i, chunk in enumerate(text_chunks, 1):
                    logger.info(f"🔄 Processing chunk {i}/{len(text_chunks)} (length: {len(chunk)})")
                    logger.debug(f"Chunk {i} preview: {chunk[:100]}...")
                    
                    audio_data = self.generate_multi_speaker_audio(
                        chunk, voice, voice2, "Host", "Guest"
                    )
                    audio_chunks.append(audio_data)
                    logger.info(f"✅ Chunk {i} processed, audio size: {len(audio_data)} bytes")
                
                # Merge all chunks into single audio file
                if len(audio_chunks) == 1:
                    logger.info(f"📦 Single chunk, returning directly")
                    final_audio = audio_chunks[0]
                else:
                    logger.info(f"🔗 Merging {len(audio_chunks)} audio chunks")
                    final_audio = self.merge_audio(audio_chunks)
                    
            else:
                logger.info(f"🗣️ Using SINGLE-SPEAKER mode")
                text_chunks = self.chunk_text(text)
                logger.info(f"📦 Text split into {len(text_chunks)} chunks for single-speaker")
                
                audio_chunks = []
                
                for i, chunk in enumerate(text_chunks, 1):
                    logger.info(f"🔄 Processing chunk {i}/{len(text_chunks)} (length: {len(chunk)})")
                    logger.debug(f"Chunk {i} preview: {chunk[:100]}...")
                    
                    audio_data = self.generate_single_speaker_audio(chunk, voice)
                    audio_chunks.append(audio_data)
                    logger.info(f"✅ Chunk {i} processed, audio size: {len(audio_data)} bytes")
                
                # Merge all chunks into single audio file
                if len(audio_chunks) == 1:
                    logger.info(f"📦 Single chunk, returning directly")
                    final_audio = audio_chunks[0]
                else:
                    logger.info(f"🔗 Merging {len(audio_chunks)} audio chunks")
                    final_audio = self.merge_audio(audio_chunks)
            
            logger.info(f"🎉 === AUDIO GENERATION COMPLETED ===")
            logger.info(f"📊 Final audio size: {len(final_audio)} bytes")
            return final_audio
        
        except Exception as e:
            logger.error(f"💥 === AUDIO GENERATION FAILED ===")
            logger.error(f"❌ Error: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to generate audio: {str(e)}") from e
    
    def get_supported_tags(self) -> List[str]:
        """Get supported tags for the new Gemini TTS API.
        
        Note: The new Gemini TTS API does not support traditional SSML tags.
        Instead, it uses:
        - Natural language instructions for style control ("Say cheerfully:", "Speak slowly:", etc.)
        - Speaker tags for multi-speaker conversations (<Host>, <Guest>, etc.)
        - Voice selection from 30 prebuilt voices
        """
        # Return empty list since this API doesn't support traditional SSML
        return []
        
    def validate_parameters(self, text: str, voice: str, model: str, voice2: str = None) -> None:
        """
        Validate input parameters before generating audio.
        
        Args:
            text (str): Input text
            voice (str): Voice ID
            model (str): Model name
            voice2 (str): Second voice ID (optional)
            
        Raises:
            ValueError: If parameters are invalid
        """
        super().validate_parameters(text, voice, model, voice2)
        
        # Additional validation for Gemini models
        if model and not model.startswith("gemini-"):
            logger.warning(f"Model '{model}' may not be a valid Gemini model") 