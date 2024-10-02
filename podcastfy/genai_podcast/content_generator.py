import google.generativeai as genai
from podcastfy.utils.config import load_config
import logging

logger = logging.getLogger(__name__)

class ContentGenerator:
	def __init__(self, api_key):
		"""
		Initialize the ContentGenerator.

		Args:
			api_key (str): API key for Google's Generative AI.
		"""
		self.api_key = api_key
		genai.configure(api_key=self.api_key)
		
		with open('specs/prompt.txt', 'r') as file:
			system_prompt = file.read()
		
		self.model = genai.GenerativeModel('gemini-1.5-pro-latest', system_instruction=system_prompt)

	def generate_qa_content(self, input_texts, output_filepath=None):
		"""
		Generate Q&A content based on input texts.

		Args:
			input_texts (str): Input texts to generate content from.
			output_filepath (str, optional): Filepath to save the response content. Defaults to None.

		Returns:
			str: Formatted Q&A content.

		Raises:
			Exception: If there's an error in generating content.
		"""
		try:
			response = self.model.generate_content(f"INPUT TEXT: {input_texts}")
			
			if output_filepath:
				with open(output_filepath, 'w') as file:
					file.write(response.text)
				logger.info(f"Response content saved to {output_filepath}")
			
			return response.text
		except Exception as e:
			logger.error(f"Error generating content: {str(e)}")
			raise

def main(seed=42):
	"""
	Generate Q&A content based on input text from input_text.txt using the Gemini API.

	Args:
		seed (int): Random seed for reproducibility. Defaults to 42.

	Returns:
		None
	"""
	try:
		# Load configuration
		config = load_config()

		# Get the Gemini API key from the configuration
		api_key = config.get('GEMINI_API_KEY')
		if not api_key:
			raise ValueError("GEMINI_API_KEY not found in configuration")

		# Initialize ContentGenerator
		content_generator = ContentGenerator(api_key)

		# Read input text from file
		import os

		input_text = ""
		transcript_dir = 'tests/data/transcripts'
		for filename in os.listdir(transcript_dir):
			if filename.endswith('.txt'):
				with open(os.path.join(transcript_dir, filename), 'r') as file:
					input_text += file.read() + "\n\n"

		# Generate Q&A content
		response = content_generator.generate_qa_content(input_text)

		# Print the generated Q&A content
		print("Generated Q&A Content:")
		# Output response text to file
		with open('tests/data/response2.txt', 'w') as file:
			file.write(response.text)

	except Exception as e:
		logger.error(f"An error occurred while generating Q&A content: {str(e)}")
		raise

if __name__ == "__main__":
	main()