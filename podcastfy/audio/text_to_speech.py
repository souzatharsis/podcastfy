import logging
from elevenlabs import client, save
from podcastfy.utils.config import load_config
from pydub import AudioSegment
import os
import re


logger = logging.getLogger(__name__)

class TextToSpeech:
	def __init__(self, api_key):
		"""
		Initialize the TextToSpeech class.

		Args:
			api_key (str): API key for ElevenLabs text-to-speech service.
		"""
		self.client = client.ElevenLabs(api_key=api_key)

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
				import os
				from uuid import uuid4

				

				# Save each chunk from question_audio as an mp3
				# Save question audio chunks
				counter += 1
				file_name = f"tests/data/audio/{counter}.mp3"
				with open(file_name, "wb") as out:
					for chunk in question_audio:
						if chunk:
							out.write(chunk)
				audio_files.append(file_name)

				# Save answer audio chunks
				counter += 1
				file_name = f"tests/data/audio/{counter}.mp3"
				with open(file_name, "wb") as out:
					for chunk in answer_audio:
						if chunk:
							out.write(chunk)
				audio_files.append(file_name)

			# Merge all audio files and save the result
			self.__merge_audio_files("tests/data/audio", 
							 output_file)

			# Clean up individual audio files
			for file in audio_files:
				os.remove(file)
			
			logger.info(f"Audio saved to {output_file}")

		except Exception as e:
			logger.error(f"Error converting text to speech: {str(e)}")
			raise

	def split_qa(self, input_text):
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

def main(seed=42):
	"""
	Main function to test the TextToSpeech class.

	Args:
		seed (int): Random seed for reproducibility. Defaults to 42.
	"""
	try:
		# Load configuration
		config = load_config()

		# Get the ElevenLabs API key from the configuration
		api_key = config.get('ELEVENLABS_API_KEY')
		if not api_key:
			raise ValueError("ELEVENLABS_API_KEY not found in configuration")

		# Initialize TextToSpeech
		tts = TextToSpeech(api_key)

		# Read input text from file
		with open('tests/data/response.txt', 'r') as file:
			input_text = file.read()

		# Convert text to speech and save as MP3
		output_file = 'tests/data/response.mp3'
		tts.convert_to_speech(input_text, output_file)

		logger.info(f"Text-to-speech conversion completed. Output saved to {output_file}")

	except Exception as e:
		logger.error(f"An error occurred during text-to-speech conversion: {str(e)}")
		raise

if __name__ == "__main__":
	main(seed=42)