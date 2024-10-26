"""
Text-to-Speech Module

This module provides functionality to convert text into speech using various TTS models.
It supports both ElevenLabs, OpenAI and Edge TTS services and handles the conversion process,
including cleaning of input text and merging of audio files.
"""

import logging
import asyncio
import edge_tts
from elevenlabs import client as elevenlabs_client
from podcastfy.utils.config import load_config
from podcastfy.utils.config_conversation import load_conversation_config
from pydub import AudioSegment
import os
import re
import openai
from typing import List, Tuple, Optional, Union, Dict, Any

logger = logging.getLogger(__name__)

class TextToSpeech:
	def __init__(self, model: str = 'edge', api_key: Optional[str] = None, conversation_config: Optional[Dict[str, Any]] = None):
		"""
		Initialize the TextToSpeech class.

		Args:
			model (str): The model to use for text-to-speech conversion. 
						 Options are 'elevenlabs', 'openai' or 'edge'. Defaults to 'edge'.
			api_key (Optional[str]): API key for the selected text-to-speech service.
						   If not provided, it will be loaded from the config.
		"""
		self.model = model.lower()
		self.config = load_config()
		self.conversation_config = load_conversation_config(conversation_config)
		self.tts_config = self.conversation_config.get('text_to_speech')

		if self.model == 'elevenlabs':
			self.api_key = api_key or self.config.ELEVENLABS_API_KEY
			self.client = elevenlabs_client.ElevenLabs(api_key=self.api_key)
		elif self.model == 'openai':
			self.api_key = api_key or self.config.OPENAI_API_KEY
			openai.api_key = self.api_key
		elif self.model == 'edge':
			pass
		else:
			raise ValueError("Invalid model. Choose 'elevenlabs', 'openai' or 'edge'.")

		self.audio_format = self.tts_config.get('audio_format')
		self.temp_audio_dir = self.tts_config.get('temp_audio_dir')
		self.ending_message = self.tts_config.get('ending_message')

		# Create temp_audio_dir if it doesn't exist
		if not os.path.exists(self.temp_audio_dir):
			os.makedirs(self.temp_audio_dir)

	def __merge_audio_files(self, input_dir: str, output_file: str) -> None:
		"""
		Merge all audio files in the input directory sequentially and save the result.

		Args:
			input_dir (str): Path to the directory containing audio files.
			output_file (str): Path to save the merged audio file.
		"""
		try:
			# Function to sort filenames naturally
			def natural_sort_key(filename: str) -> List[Union[int, str]]:
				return [int(text) if text.isdigit() else text for text in re.split(r'(\d+)', filename)]
			
			combined = AudioSegment.empty()
			audio_files = sorted(
				[f for f in os.listdir(input_dir) if f.endswith(f".{self.audio_format}")],
				key=natural_sort_key
			)
			for file in audio_files:
				if file.endswith(f".{self.audio_format}"):
					file_path = os.path.join(input_dir, file)
					combined += AudioSegment.from_file(file_path, format=self.audio_format)
			
			combined.export(output_file, format=self.audio_format)
			logger.info(f"Merged audio saved to {output_file}")
		except Exception as e:
			logger.error(f"Error merging audio files: {str(e)}")
			raise

	def convert_to_speech(self, text: str, output_file: str) -> None:
		"""
		Convert input text to speech and save as an audio file.

		Args:
			text (str): Input text to convert to speech.
			output_file (str): Path to save the output audio file.

		Raises:
			Exception: If there's an error in converting text to speech.
		"""
		# Clean TSS markup tags from the input text
		cleaned_text = self.clean_tss_markup(text)

		if self.model == 'elevenlabs':
			self.__convert_to_speech_elevenlabs(cleaned_text, output_file)
		elif self.model == 'openai':
			self.__convert_to_speech_openai(cleaned_text, output_file)
		elif self.model == 'edge':
			self.__convert_to_speech_edge(cleaned_text, output_file)

	def __convert_to_speech_elevenlabs(self, text: str, output_file: str) -> None:
		try:
			qa_pairs = self.split_qa(text)
			audio_files = []
			counter = 0
			for question, answer in qa_pairs:
				question_audio = self.client.generate(
					text=question,
					voice=self.tts_config.get("elevenlabs").get("default_voices").get("question"),
					model=self.tts_config.get("elevenlabs").get("model")
				)
				answer_audio = self.client.generate(
					text=answer,
					voice=self.tts_config.get("elevenlabs").get("default_voices").get("answer"),
					model=self.tts_config.get("elevenlabs").get("model")
				)

				# Save question and answer audio chunks
				for audio in [question_audio, answer_audio]:
					counter += 1
					file_name = f"{self.temp_audio_dir}{counter}.{self.audio_format}"
					with open(file_name, "wb") as out:
						for chunk in audio:
							if chunk:
								out.write(chunk)
					audio_files.append(file_name)

			# Merge all audio files and save the result
			self.__merge_audio_files(self.temp_audio_dir, output_file)

			# Clean up individual audio files
			for file in audio_files:
				os.remove(file)
			
			logger.info(f"Audio saved to {output_file}")

		except Exception as e:
			logger.error(f"Error converting text to speech with ElevenLabs: {str(e)}")
			raise

	def __convert_to_speech_openai(self, text: str, output_file: str) -> None:
		try:
			qa_pairs = self.split_qa(text)
			print(qa_pairs)
			audio_files = []
			counter = 0
			for question, answer in qa_pairs:
				for speaker, content in [
					(self.tts_config.get("openai").get("default_voices").get("question"), question),
					(self.tts_config.get("openai").get("default_voices").get("answer"), answer)
				]:
					counter += 1
					file_name = f"{self.temp_audio_dir}{counter}.{self.audio_format}"
					response = openai.audio.speech.create(
						model=self.tts_config.get("openai").get("model"),
						voice=speaker,
						input=content
					)
					with open(file_name, "wb") as file:
						file.write(response.content)

					audio_files.append(file_name)

			# Merge all audio files and save the result
			self.__merge_audio_files(self.temp_audio_dir, output_file)

			# Clean up individual audio files
			for file in audio_files:
				os.remove(file)
			
			logger.info(f"Audio saved to {output_file}")

		except Exception as e:
			logger.error(f"Error converting text to speech with OpenAI: {str(e)}")
			raise
	
	def get_or_create_eventloop():
		try:
			return asyncio.get_event_loop()
		except RuntimeError as ex:
			if "There is no current event loop in thread" in str(ex):
				loop = asyncio.new_event_loop()
				asyncio.set_event_loop(loop)
				return asyncio.get_event_loop()

	import nest_asyncio  # type: ignore
	get_or_create_eventloop()
	nest_asyncio.apply()

	def __convert_to_speech_edge(self, text: str, output_file: str) -> None:
		"""
		Convert text to speech using Edge TTS.

		Args:
			text (str): The input text to convert to speech.
			output_file (str): The path to save the output audio file.
		"""
		try:
			qa_pairs = self.split_qa(text)
			audio_files = []
			counter = 0

			async def edge_tts_conversion(text_chunk: str, output_path: str, voice: str):
				tts = edge_tts.Communicate(text_chunk, voice)
				await tts.save(output_path)
				return
				
			async def process_qa_pairs(qa_pairs):
				nonlocal counter
				tasks = []
				for question, answer in qa_pairs:
					for speaker, content in [
						(self.tts_config.get("edge").get("default_voices").get("question"), question),
						(self.tts_config.get("edge").get("default_voices").get("answer"), answer)
					]:
						counter += 1
						file_name = f"{self.temp_audio_dir}{counter}.{self.audio_format}"
						tasks.append(asyncio.ensure_future(edge_tts_conversion(content, file_name, speaker)))
						audio_files.append(file_name)

				await asyncio.gather(*tasks)

			asyncio.run(process_qa_pairs(qa_pairs))

			# Merge all audio files
			self.__merge_audio_files(self.temp_audio_dir, output_file)

			# Clean up individual audio files
			for file in audio_files:
				os.remove(file)
			logger.info(f"Audio saved to {output_file}")		

		except Exception as e:
			logger.error(f"Error converting text to speech with Edge: {str(e)}")
			raise


	def split_qa(self, input_text: str) -> List[Tuple[str, str]]:
		"""
		Split the input text into question-answer pairs.

		Args:
			input_text (str): The input text containing Person1 and Person2 dialogues.

		Returns:
			List[Tuple[str, str]]: A list of tuples containing (Person1, Person2) dialogues.
		"""
		# Add ending message to the end of input_text
		input_text += f"<Person2>{self.ending_message}</Person2>"

		# Regular expression pattern to match Person1 and Person2 dialogues
		pattern = r'<Person1>(.*?)</Person1>\s*<Person2>(.*?)</Person2>'
		
		# Find all matches in the input text
		matches = re.findall(pattern, input_text, re.DOTALL)
		
		# Process the matches to remove extra whitespace and newlines
		processed_matches = [
			(
				' '.join(person1.split()).strip(),
				' '.join(person2.split()).strip()
			)
			for person1, person2 in matches
		]
		return processed_matches

	# to be done: Add support for additional tags dynamically given TTS model. Right now it's the intersection of OpenAI/MS Edgeand ElevenLabs supported tags.
	def clean_tss_markup(self, input_text: str, additional_tags: List[str] = ["Person1", "Person2"]) -> str:
		"""
		Remove unsupported TSS markup tags from the input text while preserving supported SSML tags.

		Args:
			input_text (str): The input text containing TSS markup tags.
			additional_tags (List[str]): Optional list of additional tags to preserve. Defaults to ["Person1", "Person2"].

		Returns:
			str: Cleaned text with unsupported TSS markup tags removed.
		"""
		# List of SSML tags supported by both OpenAI and ElevenLabs
		supported_tags = [
			'lang', 'p', 'phoneme',
			's', 'say-as', 'sub'
		]

		# Append additional tags to the supported tags list
		supported_tags.extend(additional_tags)

		# Create a pattern that matches any tag not in the supported list
		pattern = r'</?(?!(?:' + '|'.join(supported_tags) + r')\b)[^>]+>'

		# Remove unsupported tags
		cleaned_text = re.sub(pattern, '', input_text)

		# Remove any leftover empty lines
		cleaned_text = re.sub(r'\n\s*\n', '\n', cleaned_text)

		# Ensure closing tags for additional tags are preserved
		for tag in additional_tags:
			cleaned_text = re.sub(f'<{tag}>(.*?)(?=<(?:{"|".join(additional_tags)})>|$)', 
								  f'<{tag}>\\1</{tag}>', 
								  cleaned_text, 
								  flags=re.DOTALL)
		# Remove '(scratchpad)' from cleaned_text
		cleaned_text = cleaned_text.replace('(scratchpad)', '')

		return cleaned_text.strip()

def main(seed: int = 42) -> None:
	"""
	Main function to test the TextToSpeech class.

	Args:
		seed (int): Random seed for reproducibility. Defaults to 42.
	"""
	try:
		# Load configuration
		config = load_config()

		# Read input text from file
		with open('tests/data/transcript_336aa9f955cd4019bc1287379a5a2820.txt', 'r') as file:
			input_text = file.read()

		# Test ElevenLabs
		tts_elevenlabs = TextToSpeech(model='elevenlabs')
		elevenlabs_output_file = 'tests/data/response_elevenlabs.mp3'
		tts_elevenlabs.convert_to_speech(input_text, elevenlabs_output_file)
		logger.info(f"ElevenLabs TTS completed. Output saved to {elevenlabs_output_file}")

		# Test OpenAI
		tts_openai = TextToSpeech(model='openai')
		openai_output_file = 'tests/data/response_openai.mp3'
		tts_openai.convert_to_speech(input_text, openai_output_file)
		logger.info(f"OpenAI TTS completed. Output saved to {openai_output_file}")

		# Test OpenAI
		tts_edge = TextToSpeech(model='edge')
		edge_output_file = 'tests/data/response_edge.mp3'
		tts_edge.convert_to_speech(input_text, edge_output_file)
		logger.info(f"Edge TTS completed. Output saved to {edge_output_file}")

	except Exception as e:
		logger.error(f"An error occurred during text-to-speech conversion: {str(e)}")
		raise

if __name__ == "__main__":
	main(seed=42)