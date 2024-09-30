import PyPDF2
import logging

logger = logging.getLogger(__name__)

class PDFExtractor:
	def extract_content(self, file_path):
		"""
		Extract text content from a PDF file.

		Args:
			file_path (str): Path to the PDF file.

		Returns:
			str: Extracted text content.
		"""
		try:
			with open(file_path, 'rb') as file:
				reader = PyPDF2.PdfReader(file)
				return " ".join(page.extract_text() for page in reader.pages)
		except Exception as e:
			logger.error(f"Error extracting PDF content: {str(e)}")
			raise