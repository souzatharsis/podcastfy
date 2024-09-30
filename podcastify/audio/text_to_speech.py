import logging
from elevenlabs import generate, save

logger = logging.getLogger(__name__)

class TextToSpeech:
	def __init__(self, api_key):
		self.api_key = api_key

	def convert_to_speech(self, text, output_file):
		try:
			qa_pairs = self.split_qa(text)
			audio = b""
			for question, answer in qa_pairs:
				question_audio = generate(text=question, voice="Liam", api_key=self.api_key)
				answer_audio = generate(text=answer, voice="Matilda", api_key=self.api_key)
				audio += question_audio + answer_audio
			save(audio, output_file)
		except Exception as e:
			logger.error(f"Error converting text to speech: {str(e)}")
			raise

	def split_qa(self, text):
		qa_pairs = []
		parts = text.split("<Question>")
		for part in parts[1:]:  # Skip the first empty part
			question, answer = part.split("<Answer>")
			qa_pairs.append((question.strip(), answer.strip().rstrip("</Answer>")))
		return qa_pairs