"""
Content Extractor Module

This module provides functionality to extract content from various sources including
websites, YouTube videos, and PDF files. It serves as a central hub for content
extraction, delegating to specialized extractors based on the source type.
"""

import logging
import re
from typing import List, Union
from urllib.parse import urlparse
from .youtube_transcriber import YouTubeTranscriber
from .website_extractor import WebsiteExtractor
from .pdf_extractor import PDFExtractor
from podcastfy.utils.config import load_config

logger = logging.getLogger(__name__)

class ContentExtractor:
	def __init__(self, jina_api_key: str):
		"""
		Initialize the ContentExtractor.

		Args:
			jina_api_key (str): API key for Jina AI.
		"""
		self.youtube_transcriber = YouTubeTranscriber()
		self.website_extractor = WebsiteExtractor(jina_api_key)
		self.pdf_extractor = PDFExtractor()
		self.config = load_config()
		self.content_extractor_config = self.config.get('content_extractor')

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

	def extract_content(self, source: str) -> str:
		"""
		Extract content from various sources.

		Args:
			source (str): URL or file path of the content source.

		Returns:
			str: Extracted text content.

		Raises:
			ValueError: If the source type is unsupported.
		"""
		try:
			if self.is_url(source):
				if any(pattern in source for pattern in self.content_extractor_config['youtube_url_patterns']):
					return self.youtube_transcriber.extract_transcript(source)
				else:
					return self.website_extractor.extract_content(source)
			elif source.lower().endswith('.pdf'):
				return self.pdf_extractor.extract_content(source)
			else:
				raise ValueError("Unsupported source type")
		except Exception as e:
			logger.error(f"Error extracting content from {source}: {str(e)}")
			raise