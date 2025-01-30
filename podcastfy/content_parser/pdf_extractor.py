"""
PDF Extractor Module

This module provides functionality to extract text content from PDF files.
It handles the reading of PDF files (both local and web-hosted), text extraction,
and normalization of the extracted content, including handling of special characters
and accents.
"""

import pymupdf
import logging
import os
import io
import requests
import unicodedata
from typing import Union
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class PDFExtractor:
	def _download_pdf(self, url: str) -> bytes:
		"""
		Download a PDF file from a URL.

		Args:
			url (str): The URL of the PDF file.

		Returns:
			bytes: The downloaded PDF content.

		Raises:
			requests.exceptions.RequestException: If download fails.
		"""
		try:
			response = requests.get(url, verify=True)
			response.raise_for_status()
			return response.content
		except Exception as e:
			logger.error(f"Error downloading PDF from {url}: {str(e)}")
			raise

	def _is_url(self, source: str) -> bool:
		"""Check if the source is a URL."""
		try:
			result = urlparse(source)
			return all([result.scheme, result.netloc])
		except ValueError:
			return False

	def extract_content(self, source: Union[str, bytes]) -> str:
		"""
		Extract text content from a PDF file, handling foreign characters and special characters.
		Supports both local files and web URLs. Accents are removed from the text.

		Args:
			source (Union[str, bytes]): Path to PDF file, URL, or bytes content.

		Returns:
			str: Extracted text content with accents removed and properly handled characters.

		Raises:
			ValueError: If the PDF is password-protected or corrupted.
			Exception: For other extraction errors.
		"""
		try:
			if isinstance(source, str):
				if self._is_url(source):
					content = self._download_pdf(source)
					doc = pymupdf.open(stream=content, filetype="pdf")
				else:
					doc = pymupdf.open(source)
			else:
				doc = pymupdf.open(stream=source, filetype="pdf")

			if doc.needs_pass:
				raise ValueError("PDF is password-protected")

			text_parts = []
			for page_num in range(doc.page_count):
				page = doc[page_num]
				text = page.get_text()
				if text.strip():  # Only add non-empty pages
					text_parts.append(f"Page {page_num + 1}:\n{text}")

			doc.close()
			
			if not text_parts:
				logger.warning("No text content found in PDF")
				return ""

			content = "\n\n".join(text_parts)
			
			# Normalize the text to handle special characters and remove accents
			normalized_content = unicodedata.normalize('NFKD', content)
			normalized_content = normalized_content.encode('ascii', 'ignore').decode('ascii')

			return normalized_content
		except pymupdf.fitz.FileDataError as e:
			logger.error(f"PDF file is corrupted or invalid: {str(e)}")
			raise ValueError("PDF file is corrupted or invalid")
		except Exception as e:
			logger.error(f"Error extracting PDF content: {str(e)}")
			raise

def main(seed: int = 42) -> None:
	"""
	Test the PDFExtractor class with both local and web PDFs.

	Args:
		seed (int): Random seed for reproducibility. Defaults to 42.
	"""
	import random
	random.seed(seed)

	extractor = PDFExtractor()

	# Test URLs
	test_urls = [
		"https://www.banyantree.in/jagdishpur/wp-content/uploads/2020/06/Panchatantra-.pdf",
		# Add more test URLs here
	]

	# Test local file
	script_dir = os.path.dirname(os.path.abspath(__file__))
	local_pdf_path = os.path.join(script_dir, '..', '..', 'tests', 'data', 'file.pdf')

	# Test web PDFs
	for url in test_urls:
		try:
			print(f"\nTesting URL: {url}")
			content = extractor.extract_content(url)
			print("Content extracted successfully:")
			print(content[:500] + "..." if len(content) > 500 else content)
		except Exception as e:
			print(f"Error processing {url}: {str(e)}")

	# Test local PDF
	try:
		print(f"\nTesting local file: {local_pdf_path}")
		content = extractor.extract_content(local_pdf_path)
		print("Content extracted successfully:")
		print(content[:500] + "..." if len(content) > 500 else content)
	except Exception as e:
		print(f"Error processing local file: {str(e)}")

if __name__ == "__main__":
	main()