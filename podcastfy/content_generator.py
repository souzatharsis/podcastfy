"""
Content Generator Module

This module is responsible for generating Q&A content based on input texts using
Google's Generative AI (Gemini). It handles the interaction with the AI model and
provides methods to generate and save the generated content.
"""

import google.generativeai as genai
from podcastfy.utils.config import load_config
import logging
from typing import Optional

import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def get_config_path(config_file: str = 'prompt.txt'):
	"""
	Get the path to the prompt.txt file.
	
	Returns:
		str: The path to the prompt.txt file.
	"""
	try:
		# Check if the script is running in a PyInstaller bundle
		if getattr(sys, 'frozen', False):
			base_path = sys._MEIPASS
		else:
			base_path = os.path.dirname(os.path.abspath(__file__))
		
		# Look for prompt.txt in the same directory as the script
		config_path = os.path.join(base_path, 'prompt.txt')
		if os.path.exists(config_path):
			return config_path
		
		# If not found, look in the parent directory (package root)
		config_path = os.path.join(os.path.dirname(base_path), 'prompt.txt')
		if os.path.exists(config_path):
			return config_path
		
		# If still not found, look in the current working directory
		config_path = os.path.join(os.getcwd(), 'prompt.txt')
		if os.path.exists(config_path):
			return config_path
		
		raise FileNotFoundError("prompt.txt not found")
	
	except Exception as e:
		print(f"Error locating prompt.txt: {str(e)}")
		return None

class ContentGenerator:
	def __init__(self, api_key: str):
		"""
		Initialize the ContentGenerator.

		Args:
			api_key (str): API key for Google's Generative AI.
		"""
		self.api_key = api_key
		genai.configure(api_key=self.api_key)
		
		self.config = load_config()
		self.content_generator_config = self.config.get('content_generator', {})
		
		system_prompt_file = self.content_generator_config.get('system_prompt_file')
		system_prompt_file = get_config_path(system_prompt_file)
		with open(system_prompt_file, 'r') as file:
			system_prompt = file.read()
		
		self.model = genai.GenerativeModel(
			self.content_generator_config.get('gemini_model', 'gemini-1.5-pro-latest'),
			system_instruction=system_prompt
		)

	def generate_qa_content(self, input_texts: str, output_filepath: Optional[str] = None) -> str:
		"""
		Generate Q&A content based on input texts.

		Args:
			input_texts (str): Input texts to generate content from.
			output_filepath (Optional[str]): Filepath to save the response content. Defaults to None.

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

def main(seed: int = 42) -> None:
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
		api_key = config.GEMINI_API_KEY
		if not api_key:
			raise ValueError("GEMINI_API_KEY not found in configuration")

		# Initialize ContentGenerator
		content_generator = ContentGenerator(api_key)

		# Read input text from file
		import os

		input_text = ""
		transcript_dir = config.get('output_directories', {}).get('transcripts', 'data/transcripts')
		for filename in os.listdir(transcript_dir):
			if filename.endswith('.txt'):
				with open(os.path.join(transcript_dir, filename), 'r') as file:
					input_text += file.read() + "\n\n"

		# Generate Q&A content
		response = content_generator.generate_qa_content(input_text)

		# Print the generated Q&A content
		print("Generated Q&A Content:")
		# Output response text to file
		output_file = os.path.join(config.get('output_directories', {}).get('transcripts', 'data/transcripts'), 'response.txt')
		with open(output_file, 'w') as file:
			file.write(response)

	except Exception as e:
		logger.error(f"An error occurred while generating Q&A content: {str(e)}")
		raise

if __name__ == "__main__":
	main()