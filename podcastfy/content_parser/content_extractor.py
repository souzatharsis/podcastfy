"""
Content Extractor Module

This module provides functionality to extract content from various sources including
websites, YouTube videos, PDF files, and Microsoft Office documents. It serves as a
central hub for content extraction, delegating to specialized extractors based on
the source type.
"""

import logging
import re
from typing import List, Union
from urllib.parse import urlparse
from .youtube_transcriber import YouTubeTranscriber
from .website_extractor import WebsiteExtractor
from .pdf_extractor import PDFExtractor
from .office_extractor import OfficeExtractor
from .text_extractor import TextExtractor
from podcastfy.utils.config import load_config

logger = logging.getLogger(__name__)

class ContentExtractor:
	def __init__(self):
		"""
		Initialize the ContentExtractor with specialized extractors for different content types.
		"""
		self.youtube_transcriber = YouTubeTranscriber()
		self.website_extractor = WebsiteExtractor()
		self.pdf_extractor = PDFExtractor()
		self.office_extractor = OfficeExtractor()
		self.text_extractor = TextExtractor()
		self.config = load_config()
		self.content_extractor_config = self.config.get('content_extractor', {})

	def is_url(self, source: str) -> bool:
		"""
		Check if the given source is a valid URL.

		Args:
			source (str): The source to check.

		Returns:
			bool: True if the source is a valid URL, False otherwise.
		"""
		try:
			# If the source doesn't start with a scheme, add 'https://'
			if not source.startswith(('http://', 'https://')):
				source = 'https://' + source

			result = urlparse(source)
			return all([result.scheme, result.netloc])
		except ValueError:
			return False

	def _get_file_extension(self, source: str) -> str:
		"""Get the file extension from a source path or URL."""
		return source.lower().split('.')[-1] if '.' in source else ''

	def extract_content(self, source: Union[str, bytes]) -> str:
		"""
		Extract content from various sources.

		Args:
			source (Union[str, bytes]): URL, file path, or bytes content of the source.

		Returns:
			str: Extracted text content.

		Raises:
			ValueError: If the source type is unsupported or invalid.
			Exception: For other extraction errors.
		"""
		try:
			if isinstance(source, bytes):
				# Try to detect file type from content
				# For now, assume PDF if bytes are provided
				return self.pdf_extractor.extract_content(source)

			source_lower = source.lower()
			
			# Handle YouTube URLs
			if self.is_url(source) and any(pattern in source_lower for pattern in self.content_extractor_config['youtube_url_patterns']):
				return self.youtube_transcriber.extract_transcript(source)

			# Handle file extensions
			extension = self._get_file_extension(source_lower)
			
			if extension in ['pdf']:
				return self.pdf_extractor.extract_content(source)
			elif extension in ['doc', 'docx']:
				return self.office_extractor.extract_docx(source)
			elif extension in ['xls', 'xlsx', 'xlsm']:
				return self.office_extractor.extract_excel(source)
			elif extension in ['ppt', 'pptx']:
				return self.office_extractor.extract_pptx(source)
			elif extension in ['txt', 'text']:
				# Use the new TextExtractor for text files
				return self.text_extractor.extract_content(source)
			elif self.is_url(source):
				# If it's a URL but not a specific file type, treat as website
				return self.website_extractor.extract_content(source)
			else:
				raise ValueError(f"Unsupported source type or file extension: {extension}")

		except Exception as e:
			logger.error(f"Error extracting content from {source}: {str(e)}")
			raise

	def generate_topic_content(self, topic: str) -> str:
		"""
		Generate content based on a given topic using a generative model.

		Args:
			topic (str): The topic to generate content for.

		Returns:
			str: Generated content based on the topic.
		"""
		try:
			import google.generativeai as genai

			model = genai.GenerativeModel('models/gemini-1.5-flash-002')
			topic_prompt = f'Be detailed. Search for {topic}'
			response = model.generate_content(contents=topic_prompt, tools='google_search_retrieval')
			
			return response.candidates[0].content.parts[0].text
		except Exception as e:
			logger.error(f"Error generating content for topic '{topic}': {str(e)}")
			raise

def main(seed: int = 42) -> None:
	"""
	Main function to test the ContentExtractor class.
	"""
	logging.basicConfig(level=logging.INFO)

	# Create an instance of ContentExtractor
	extractor = ContentExtractor()

	# Test sources
	test_sources: List[str] = [
		"www.souzatharsis.com",
		"https://www.youtube.com/watch?v=dQw4w9WgXcQ",
		"https://www.banyantree.in/jagdishpur/wp-content/uploads/2020/06/Panchatantra-.pdf",
		"https://calibre-ebook.com/downloads/demos/demo.docx",
		"https://www.cmu.edu/blackboard/files/evaluate/tests-example.xls",
		"https://scholar.harvard.edu/files/torman_personal/files/samplepptx.pptx",
		"https://example-files.online-convert.com/document/txt/example.txt",
		"https://www.w3.org/TR/2003/REC-PNG-20031110/iso_8859-1.txt"
	]

	for source in test_sources:
		try:
			logger.info(f"Extracting content from: {source}")
			content = extractor.extract_content(source)

			# Print the first 500 characters of the extracted content
			logger.info(f"Extracted content (first 500 characters):\n{content[:500]}...")

			# Print the total length of the extracted content
			logger.info(f"Total length of extracted content: {len(content)} characters")
			logger.info("-" * 50)

		except Exception as e:
			logger.error(f"An error occurred while processing {source}: {str(e)}")

if __name__ == "__main__":
	main()
