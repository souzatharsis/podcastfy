import logging
from elevenlabs import client as elevenlabs_client
from podcastfy.utils.config import load_config
from pydub import AudioSegment
import os
import re
import openai

logger = logging.getLogger(__name__)

class TextToSpeech:
	def __init__(self, model='elevenlabs', api_key=None):
		"""
		Initialize the TextToSpeech class.

		Args:
			model (str): The model to use for text-to-speech conversion. 
						 Options are 'elevenlabs' or 'openai'. Defaults to 'elevenlabs'.
			api_key (str): API key for the selected text-to-speech service.
						   If not provided, it will be loaded from the config.
		"""
		self.model = model.lower()
		config = load_config()

		if self.model == 'elevenlabs':
			self.api_key = api_key or config.get('ELEVENLABS_API_KEY')
			self.client = elevenlabs_client.ElevenLabs(api_key=self.api_key)
		elif self.model == 'openai':
			self.api_key = api_key or config.get('OPENAI_API_KEY')
			openai.api_key = self.api_key
		else:
			raise ValueError("Invalid model. Choose 'elevenlabs' or 'openai'.")

	def __merge_audio_files(self, input_dir, output_file):
		"""
		Merge all audio files in the input directory sequentially and save the result.

		Args:
			input_dir (str): Path to the directory containing audio files.
			output_file (str): Path to save the merged audio file.
		"""
		try:
			# Function to sort filenames naturally
			def natural_sort_key(filename):
				return [int(text) if text.isdigit() else text for text in re.split(r'(\d+)', filename)]
			
			combined = AudioSegment.empty()
			audio_files = sorted(
				[f for f in os.listdir(input_dir) if f.endswith(".mp3") or f.endswith(".wav")],
				key=natural_sort_key
			)
			for file in audio_files:
				if file.endswith(".mp3"):
					file_path = os.path.join(input_dir, file)
					combined += AudioSegment.from_mp3(file_path)
			
			combined.export(output_file, format="mp3")
			logger.info(f"Merged audio saved to {output_file}")
		except Exception as e:
			logger.error(f"Error merging audio files: {str(e)}")
			raise

	def convert_to_speech(self, text, output_file):
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
		print(cleaned_text)
		if self.model == 'elevenlabs':
			self.__convert_to_speech_elevenlabs(cleaned_text, output_file)
		elif self.model == 'openai':
			self.__convert_to_speech_openai(cleaned_text, output_file)

	def __convert_to_speech_elevenlabs(self, text, output_file):
		try:
			qa_pairs = self.split_qa(text)
			audio_files = []
			counter = 0
			for question, answer in qa_pairs:
				question_audio = self.client.generate(
					text=question,
					voice="Chris",
					model="eleven_multilingual_v2"
				)
				answer_audio = self.client.generate(
					text=answer,
					voice="BrittneyHart",
					model="eleven_multilingual_v2"
				)

				# Save question and answer audio chunks
				for audio in [question_audio, answer_audio]:
					counter += 1
					file_name = f"tests/data/audio/tmp/{counter}.mp3"
					with open(file_name, "wb") as out:
						for chunk in audio:
							if chunk:
								out.write(chunk)
					audio_files.append(file_name)

			# Merge all audio files and save the result
			self.__merge_audio_files("tests/data/audio/tmp", output_file)

			# Clean up individual audio files
			for file in audio_files:
				os.remove(file)
			
			logger.info(f"Audio saved to {output_file}")

		except Exception as e:
			logger.error(f"Error converting text to speech with ElevenLabs: {str(e)}")
			raise

	def __convert_to_speech_openai(self, text, output_file):
		try:
			qa_pairs = self.split_qa(text)
			print(qa_pairs)
			audio_files = []
			counter = 0
			for question, answer in qa_pairs:
				for speaker, content in [("echo", question), ("shimmer", answer)]:
					counter += 1
					file_name = f"tests/data/audio/tmp/{counter}.mp3"
					response = openai.audio.speech.create(
						model="tts-1-hd",
						voice=speaker,
						input=content
					)
					with open(file_name, "wb") as file:
						file.write(response.content)

					audio_files.append(file_name)

			# Merge all audio files and save the result
			self.__merge_audio_files("tests/data/audio/tmp", output_file)

			# Clean up individual audio files
			for file in audio_files:
				os.remove(file)
			
			logger.info(f"Audio saved to {output_file}")

		except Exception as e:
			logger.error(f"Error converting text to speech with OpenAI: {str(e)}")
			raise

	def split_qa(self, input_text): #TODO static tag + Bye Bye ending
		"""
		Split the input text into question-answer pairs.

		Args:
			input_text (str): The input text containing Person1 and Person2 dialogues.

		Returns:
			list: A list of tuples containing (Person1, Person2) dialogues.
		"""
		# Add <Person2></Person2> to the end of input_text
		input_text += "<Person2>See ya!</Person2>"

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

	def clean_tss_markup(self, input_text, additional_tags=["Person1", "Person2"]):
		"""
		Remove unsupported TSS markup tags from the input text while preserving supported SSML tags.

		Args:
			input_text (str): The input text containing TSS markup tags.
			additional_tags (list): Optional list of additional tags to preserve. Defaults to ["Person1", "Person2"].

		Returns:
			str: Cleaned text with unsupported TSS markup tags removed.
		"""
		# List of SSML tags supported by both OpenAI and ElevenLabs
		supported_tags = [
			'speak', 'break', 'lang', 'p', 'phoneme', 
			's', 'say-as', 'sub', 'voice'
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

		return cleaned_text.strip()

def main(seed=42):
	"""
	Main function to test the TextToSpeech class.

	Args:
		seed (int): Random seed for reproducibility. Defaults to 42.
	"""
	try:
		# Load configuration
		config = load_config()

		# Read input text from file
		with open('tests/data/response.txt', 'r') as file:
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

	except Exception as e:
		logger.error(f"An error occurred during text-to-speech conversion: {str(e)}")
		raise

if __name__ == "__main__":
	main(seed=42)