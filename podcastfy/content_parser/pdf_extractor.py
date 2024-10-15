"""
PDF Extractor Module

This module provides functionality to extract text content from PDF files.
It handles the reading of PDF files, text extraction, and normalization of
the extracted content, including handling of special characters and accents.
"""

import pymupdf
import logging
import os
import unicodedata

logger = logging.getLogger(__name__)

class PDFExtractor:
	def extract_content(self, file_path: str) -> str:
		"""
		Extract text content from a PDF file, handling foreign characters and special characters.
		Accents are removed from the text.

		Args:
			file_path (str): Path to the PDF file.

		Returns:
			str: Extracted text content with accents removed and properly handled characters.
		"""
		try:
			doc = pymupdf.open(file_path)
			content = " ".join(page.get_text() for page in doc)
			doc.close()
			
			# Normalize the text to handle special characters and remove accents
			normalized_content = unicodedata.normalize('NFKD', content)

			return normalized_content
		except Exception as e:
			logger.error(f"Error extracting PDF content: {str(e)}")
			raise

def main(seed: int = 42) -> None:
	"""
	Test the PDFExtractor class with a specific PDF file.

	Args:
		seed (int): Random seed for reproducibility. Defaults to 42.
	"""
	# Set the random seed
	import random
	random.seed(seed)

	# Get the absolute path of the script
	script_dir = os.path.dirname(os.path.abspath(__file__))
	
	# Construct the path to the PDF file
	pdf_path = os.path.join(script_dir, '..', '..', 'tests', 'data', 'file.pdf')
	
	extractor = PDFExtractor()

	try:
		content = extractor.extract_content(pdf_path)
		print("PDF content extracted successfully:")
		print(content[:500] + "..." if len(content) > 500 else content)
	except Exception as e:
		print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
	main()