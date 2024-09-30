import logging
import re
from urllib.parse import urlparse
from .youtube_transcriber import YouTubeTranscriber
from .website_extractor import WebsiteExtractor
from .pdf_extractor import PDFExtractor

logger = logging.getLogger(__name__)

class ContentExtractor:
	def __init__(self, jina_api_key):
		"""
		Initialize the ContentExtractor.

		Args:
			jina_api_key (str): API key for Jina AI.
		"""
		self.youtube_transcriber = YouTubeTranscriber()
		self.website_extractor = WebsiteExtractor(jina_api_key)
		self.pdf_extractor = PDFExtractor()

	def is_url(self, source):
		"""
		Check if the given source is a valid URL.

		Args:
			source (str): The source to check.

		Returns:
			bool: True if the source is a valid URL, False otherwise.
		"""
		try:
			result = urlparse(source)
			return all([result.scheme, result.netloc])
		except ValueError:
			return False

	def extract_content(self, source):
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
				if re.search(r'youtube\.com|youtu\.be', source):
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