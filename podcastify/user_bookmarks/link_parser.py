import re
import logging

logger = logging.getLogger(__name__)

class LinkParser:
	def __init__(self):
		self.url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

	def parse_links(self, text):
		"""
		Parse links from the given text.

		Args:
			text (str): Input text to search for links.

		Returns:
			list: List of found links.
		"""
		try:
			return self.url_pattern.findall(text)
		except Exception as e:
			logger.error(f"Error parsing links: {str(e)}")
			return []

	def validate_link(self, link):
		"""
		Validate if the given link is supported.

		Args:
			link (str): URL to validate.

		Returns:
			bool: True if the link is supported, False otherwise.
		"""
		supported_domains = ['youtube.com', 'youtu.be', 'medium.com', 'github.com']
		return any(domain in link for domain in supported_domains) or link.endswith('.pdf')