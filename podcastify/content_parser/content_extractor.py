import logging
from .youtube_transcriber import YouTubeTranscriber
from .website_extractor import WebsiteExtractor
from .pdf_extractor import PDFExtractor

logger = logging.getLogger(__name__)

class ContentExtractor:
	def __init__(self, jina_api_key):
		self.youtube_transcriber = YouTubeTranscriber()
		self.website_extractor = WebsiteExtractor(jina_api_key)
		self.pdf_extractor = PDFExtractor()

	def extract_content(self, source):
		"""
		Extract content from various sources.

		Args:
			source (str): URL or file path of the content source.

		Returns:
			str: Extracted text content.
		"""
		try:
			if source.startswith('http'):
				if 'youtube.com' in source or 'youtu.be' in source:
					return self.youtube_transcriber.extract_transcript(source)
				else:
					return self.website_extractor.extract_content(source)
			elif source.endswith('.pdf'):
				return self.pdf_extractor.extract_content(source)
			else:
				raise ValueError("Unsupported source type")
		except Exception as e:
			logger.error(f"Error extracting content from {source}: {str(e)}")
			raise