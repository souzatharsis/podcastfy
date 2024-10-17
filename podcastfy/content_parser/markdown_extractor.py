"""
Markdown Extractor Module

This module provides functionality to extract content from Markdown files.
"""

import logging
import markdown
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class MarkdownExtractor:
	def extract_content(self, file_path: str) -> str:
		"""
		Extract content from a markdown file.

		Args:
			file_path (str): Path to the markdown file.

		Returns:
			str: Extracted text content.

		Raises:
			Exception: If an error occurs during extraction.
		"""
		try:
			with open(file_path, 'r', encoding='utf-8') as file:
				md_content = file.read()
			html_content = markdown.markdown(md_content)
			
			# Use BeautifulSoup to extract text from HTML
			soup = BeautifulSoup(html_content, 'html.parser')
			text_content = soup.get_text(separator='\n', strip=True)
			
			return text_content
		except Exception as e:
			logger.error(f"Failed to extract content from markdown file {file_path}: {str(e)}")
			raise
