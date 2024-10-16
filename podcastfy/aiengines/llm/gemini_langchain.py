"""
Content Generator Module

This module is responsible for generating Q&A content based on input texts using
LangChain and Google's Generative AI (Gemini). It handles the interaction with the AI model and
provides methods to generate and save the generated content.
"""

import os
import re
from typing import Optional, Dict, Any, List, Tuple

from langchain_community.llms.llamafile import Llamafile
from langchain_core.prompts import HumanMessagePromptTemplate, ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langchain import hub

from podcastfy.content_generator import ContentGenerator
from podcastfy.core.character import Character
from podcastfy.aiengines.llm.base import LLMBackend
from podcastfy.core.content import Content
from podcastfy.utils.config_conversation import load_conversation_config
from podcastfy.utils.config import load_config
import logging

logger = logging.getLogger(__name__)



class OldContentGenerator:
	# note: to be deleted but stays around few days for reference and troubleshooting
	def __init__(self, api_key: str, conversation_config: Optional[Dict[str, Any]] = None):
		"""
		Initialize the ContentGenerator.

		Args:
			api_key (str): API key for Google's Generative AI.
			conversation_config (Optional[Dict[str, Any]]): Custom conversation configuration.
		"""
		os.environ["GOOGLE_API_KEY"] = api_key
		self.config = load_config()
		self.content_generator_config = self.config.get('content_generator', {})

		# Load default conversation config and update with custom config if provided

		self.config_conversation = load_conversation_config(conversation_config)

		self.llm = ChatGoogleGenerativeAI(
			model=self.content_generator_config.get('gemini_model', 'gemini-1.5-pro-latest'),
			temperature=self.config_conversation.get('creativity', 0),
			max_output_tokens=self.content_generator_config.get('max_output_tokens', 8192),
		)

		#pick podcastfy prompt from langchain hub
		self.prompt_template = hub.pull(self.config.get('content_generator', {}).get('prompt_template', 'souzatharsis/podcastfy_'))
		self.ending_message = self.config.get('text_to_speech')['ending_message']

		self.parser = StrOutputParser()

		self.chain = (self.prompt_template | self.llm | self.parser)

	def generate_qa_content(self, input_texts: str, output_filepath: Optional[str] = None, characters: List[Character] = None) -> str:
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
		assert len(characters) == 2, "The number of characters should be 2 for this implementation"
		try:


			prompt_params = {
				"input_text": input_texts,
				"word_count": self.config_conversation.get('word_count'),
				"conversation_style": ", ".join(self.config_conversation.get('conversation_style', [])),
				"roles_person1": characters[0].role,
				"roles_person2": characters[1].role,
				"dialogue_structure": ", ".join(self.config_conversation.get('dialogue_structure', [])),
				"podcast_name": self.config_conversation.get('podcast_name'),
				"podcast_tagline": self.config_conversation.get('podcast_tagline'),
				"output_language": self.config_conversation.get('output_language'),
				"engagement_techniques": ", ".join(self.config_conversation.get('engagement_techniques', []))
			}

			self.response = self.chain.invoke(prompt_params)

			logger.info(f"Content generated successfully")

			if output_filepath:
				with open(output_filepath, 'w') as file:
					file.write(self.response)
				logger.info(f"Response content saved to {output_filepath}")

			return self.response
		except Exception as e:
			logger.error(f"Error generating content: {str(e)}")
			raise

class LLMBackend:
    def __init__(
        self,
        is_local: bool,
        temperature: float,
        max_output_tokens: int,
        model_name: str,
    ):
        """
        Initialize the LLMBackend.

        Args:
                is_local (bool): Whether to use a local LLM or not.
                temperature (float): The temperature for text generation.
                max_output_tokens (int): The maximum number of output tokens.
                model_name (str): The name of the model to use.
        """
        self.is_local = is_local
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.model_name = model_name
        self.is_multimodal = not is_local  # Does not assume local LLM is multimodal

        if is_local:
            self.llm = Llamafile()
        else:
            self.llm = ChatGoogleGenerativeAI(
                model=model_name,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )



class DefaultPodcastifyTranscriptEngine(LLMBackend):
	def __init__(self, api_key: str, conversation_config: Optional[Dict[str, Any]] = None, is_local: bool = False):
		"""
		Initialize the DefaultPodcastifyTranscriptEngine.

		Args:
			api_key (str): API key for Google's Generative AI.
			conversation_config (Optional[Dict[str, Any]]): Custom conversation configuration.
		"""
		self.content_generator = ContentGenerator(api_key, conversation_config)
		self.is_local = is_local

	def split_qa(self, input_text: str) -> List[Tuple[str, str]]:
		"""
		Split the input text into question-answer pairs.

		Args:
			input_text (str): The input text containing Person1 and Person2 dialogues.

		Returns:
			List[Tuple[str, str]]: A list of tuples containing (Person1, Person2) dialogues.
		"""
		# Add ending message to the end of input_text
		input_text += f"<Person2>{self.content_generator.ending_message}</Person2>"

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

	def generate_transcript(self, content: List[Content], characters: List[Character]) -> List[Tuple[Character, str]]:
		image_file_paths = [c.value for c in content if c.type == 'image_path']
		text_content = "\n\n".join(c.value for c in content if c.type == 'text')
		content = self.content_generator.generate_qa_content(text_content, image_file_paths, is_local=self.is_local) # ideally in the future we pass characters here

		q_a_pairs = self.split_qa(content)
		transcript = []
		for q_a_pair in q_a_pairs:
			# Assign the speakers based on the order of the characters
			speaker1, speaker2 = characters
			speaker_1_text, speaker_2_text = q_a_pair
			transcript.append((speaker1, speaker_1_text))
			transcript.append((speaker2, speaker_2_text))
		return transcript

	# def generate_transcript(self, prompt: str, characters: List[Character]) -> List[Tuple[Character, str]]:
	# 	content = self.content_generator.generate_qa_content(prompt, output_filepath=None, characters=characters)
	#
	# 	# Parse the generated content into the required format
	# 	transcript = []
	# 	for line in content.split('\n'):
	# 		if ':' in line:
	# 			speaker_name, text = line.split(':', 1)
	# 			speaker = next((char for char in characters if char.name == speaker_name.strip()), None)
	# 			if speaker:
	# 				transcript.append((speaker, text.strip()))
	#
	# 	return transcript



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
		content_generator = DefaultPodcastifyTranscriptEngine(api_key)

		# Read input text from file
		input_text = ""
		transcript_dir = config.get('output_directories', {}).get('transcripts', 'data/transcripts')
		for filename in os.listdir(transcript_dir):
			if filename.endswith('.txt'):
				with open(os.path.join(transcript_dir, filename), 'r') as file:
					input_text += file.read() + "\n\n"

		# Generate Q&A content
		config_conv = load_conversation_config()
		characters = [
			Character(name="Speaker 1", role=config_conv.get('roles_person1')),
			Character(name="Speaker 2", role=config_conv.get('roles_person2')),
		]
		response = content_generator.generate_transcript(input_text, characters)

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