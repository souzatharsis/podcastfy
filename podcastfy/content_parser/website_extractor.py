import requests
import logging
import json
import re
import html
from podcastfy.utils.config import load_config

logger = logging.getLogger(__name__)

class WebsiteExtractor:
	def __init__(self, jina_api_key):
		"""
		Initialize the WebsiteExtractor.

		Args:
			jina_api_key (str): API key for Jina AI.
		"""
		self.jina_api_url = 'https://r.jina.ai'
		self.headers = {
			'Authorization': f'Bearer {jina_api_key}',
			'Content-Type': 'application/json'
		}

	def extract_content(self, url):
		"""
		Extract clean text content from a website.

		Args:
			url (str): Website URL.

		Returns:
			str: Extracted clean text content.

		Raises:
			Exception: If there's an error in extracting the content.
		"""
		try:
			payload = json.dumps({"url": url})
			response = requests.post(self.jina_api_url, headers=self.headers, data=payload)
			response.raise_for_status()  # Raise an exception for bad status codes
			
			content = response.text
			logger.debug(f"Raw response: {content[:100]}...")
			
			# The response is in markdown format
			markdown_content = content
			return self.clean_markdown(markdown_content)
		except requests.RequestException as e:
			logger.error(f"Request error: {str(e)}")
			raise Exception(f"Failed to extract content from {url}: {str(e)}")
		except Exception as e:
			logger.error(f"Unexpected error: {str(e)}")
			raise Exception(f"An unexpected error occurred while extracting content from {url}: {str(e)}")

	def clean_markdown(self, markdown_content):
		"""
		Remove images, special markdown tags, URIs, and leftover brackets from the content.
		Also remove specific headers and their content.

		Args:
			markdown_content (str): The markdown content to clean.

		Returns:
			str: Cleaned text content.
		"""
		# Decode HTML entities
		cleaned_content = html.unescape(markdown_content)

		# Remove image markdown
		image_pattern = r'!\[.*?\]\(.*?\)'
		cleaned_content = re.sub(image_pattern, '', cleaned_content)

		# Remove inline links and URIs
		link_pattern = r'\[([^\]]+)\]\([^\)]+\)'
		cleaned_content = re.sub(link_pattern, r'\1', cleaned_content)
		uri_pattern = r'https?://\S+|www\.\S+'
		cleaned_content = re.sub(uri_pattern, '', cleaned_content)

		# Remove special markdown tags (e.g., bold, italic, code)
		special_tags_pattern = r'(\*{1,2}|_{1,2}|`)'
		cleaned_content = re.sub(special_tags_pattern, '', cleaned_content)

		# Remove any remaining markdown headers
		header_pattern = r'^#+\s'
		cleaned_content = re.sub(header_pattern, '', cleaned_content, flags=re.MULTILINE)

		# Remove horizontal rules
		hr_pattern = r'^\s*[-*_]{3,}\s*$'
		cleaned_content = re.sub(hr_pattern, '', cleaned_content, flags=re.MULTILINE)

		# Remove blockquotes
		blockquote_pattern = r'^>\s'
		cleaned_content = re.sub(blockquote_pattern, '', cleaned_content, flags=re.MULTILINE)

		# Remove extra newlines
		cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)

		# Remove leftover brackets from images and links
		leftover_brackets_pattern = r'\[|\]|\(|\)'
		cleaned_content = re.sub(leftover_brackets_pattern, '', cleaned_content)

		# Remove specific headers and their content
		title_pattern = r'^Title:.*\n'
		url_source_pattern = r'^URL Source:.*\n'
		markdown_content_pattern = r'^Markdown Content:\n'
		warning_pattern = r'^Warning:.*\n'
		cleaned_content = re.sub(title_pattern, '', cleaned_content, flags=re.MULTILINE)
		cleaned_content = re.sub(url_source_pattern, '', cleaned_content, flags=re.MULTILINE)
		cleaned_content = re.sub(markdown_content_pattern, '', cleaned_content, flags=re.MULTILINE)
		cleaned_content = re.sub(warning_pattern, '', cleaned_content, flags=re.MULTILINE)

		return cleaned_content.strip()

def main():
	# Set up logging
	logging.basicConfig(level=logging.DEBUG)  # Changed to DEBUG for more detailed logs

	# Load configuration
	config = load_config()

	# Get the Jina API key from the configuration
	jina_api_key = config.get('JINA_API_KEY')

	if not jina_api_key:
		logger.error("Jina API key not found in configuration.")
		return

	# Create an instance of WebsiteExtractor 
	extractor = WebsiteExtractor(jina_api_key)

	# Test URL
	test_url = "http://www.souzatharsis.com"

	try:
		# Extract content from the test URL
		content = extractor.extract_content(test_url)

		# Print the first 500 characters of the extracted content
		logger.info(f"Extracted content (first 500 characters):\n{content[:500]}...")

		# Print the total length of the extracted content
		logger.info(f"Total length of extracted content: {len(content)} characters")

	except Exception as e:
		logger.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
	main()