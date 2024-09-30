import unittest
from podcastify.utils.config import load_config
from podcastify.content_parser.content_extractor import ContentExtractor
from podcastify.content_parser.youtube_transcriber import YouTubeTranscriber
from podcastify.content_parser.website_extractor import WebsiteExtractor
from podcastify.content_parser.pdf_extractor import PDFExtractor


class TestContentParser(unittest.TestCase):
	def test_content_extractor(self):
		# Add tests for ContentExtractor
		pass

	def test_youtube_transcriber(self):
		# Add tests for YouTubeTranscriber
		pass

	def test_website_extractor(self):
		"""
		Test the WebsiteExtractor class to ensure it correctly extracts content from a website.
		"""
		# Initialize WebsiteExtractor
		config = load_config()
		jina_api_key = config.get('JINA_API_KEY')
		extractor = WebsiteExtractor(jina_api_key)

		# Test URL
		test_url = "http://www.souzatharsis.com"

		# Extract content
		extracted_content = extractor.extract_content(test_url)
		print(extracted_content)
		# Load expected content from website.md file
		with open('./tests/data/website.md', 'r') as f:
			expected_content = f.read()

		# Assert that the extracted content matches the expected content
		self.assertEqual(extracted_content.strip(), expected_content.strip())

	def test_pdf_extractor(self):
		# Add tests for PDFExtractor
		pass

if __name__ == '__main__':
	unittest.main()