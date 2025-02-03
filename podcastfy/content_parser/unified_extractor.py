"""
Unified Content Extractor Module

This module provides a unified approach to extract content from various file formats
using the markitdown library from Microsoft. It supports multiple file formats including
PDF, Office documents (DOCX, XLS, XLSX, PPT, PPTX), text files, images, and audio files.
"""

import logging
import io
import requests
from typing import Union
from urllib.parse import urlparse
from markitdown import MarkItDown
import unicodedata
import re
import tempfile
import os

logger = logging.getLogger(__name__)

class UnifiedExtractor:
    def __init__(self):
        """Initialize the UnifiedExtractor with markitdown."""
        self.converter = MarkItDown()

    def _download_file(self, url: str) -> bytes:
        """
        Download a file from a URL.

        Args:
            url (str): The URL of the file to download.

        Returns:
            bytes: The downloaded file content.
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, verify=True, headers=headers)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Error downloading file from {url}: {str(e)}")
            raise

    def _is_url(self, source: str) -> bool:
        """Check if the source is a URL."""
        try:
            result = urlparse(source)
            logger.info(f"URL parsed: {result}")
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    def _clean_markdown(self, markdown_text: str) -> str:
        """
        Clean the markdown text by removing unnecessary formatting and normalizing text.

        Args:
            markdown_text (str): The markdown text to clean.

        Returns:
            str: Cleaned text content.
        """
        # Remove markdown images
        cleaned = re.sub(r'!\[.*?\]\(.*?\)', '', markdown_text)
        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        # Normalize unicode characters
        cleaned = unicodedata.normalize('NFKD', cleaned)
        cleaned = cleaned.encode('ascii', 'ignore').decode('ascii')
        logger.info("Markdown cleaned successfully")
        
        return cleaned.strip()

    def extract_content(self, source: Union[str, bytes]) -> str:
        """
        Extract text content from various file formats using markitdown.
        Supports both local files and web URLs.

        Args:
            source (Union[str, bytes]): Path to file, URL, or bytes content.

        Returns:
            str: Extracted text content.

        Raises:
            ValueError: If the file format is unsupported or file is invalid.
            Exception: For other extraction errors.
        """
        try:
            # Handle bytes input
            if isinstance(source, bytes):
                # Save bytes to a temporary file for markitdown to process
                with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as temp_file:
                    logger.info("Writing bytes content to temp file")
                    temp_file.write(source)
                    temp_path = temp_file.name
                try:
                    result = self.converter.convert(temp_path)
                    logger.info("Content extracted successfully")
                    markdown_text = result.text_content
                    logger.info("Markdown content extracted")
                finally:
                    os.unlink(temp_path)  # Clean up temp file
            # Handle string input (URL or file path)
            elif isinstance(source, str):
                if self._is_url(source):
                    content = self._download_file(source)
                    logger.info("File downloaded successfully")
                    # Try to determine file extension from URL
                    ext = os.path.splitext(source)[1] or '.bin'
                    # Save content to a temporary file for markitdown to process
                    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
                        temp_file.write(content)
                        temp_path = temp_file.name
                    try:
                        result = self.converter.convert(temp_path)
                        logger.info("Content extracted successfully")
                        markdown_text = result.text_content
                    finally:
                        os.unlink(temp_path)  # Clean up temp file
                else:
                    # Local file path
                    result = self.converter.convert(source)
                    markdown_text = result.text_content
            else:
                raise ValueError("Source must be either string (path/URL) or bytes")

            # Clean and normalize the markdown text
            cleaned_text = self._clean_markdown(markdown_text)
            
            if not cleaned_text:
                logger.warning("No content extracted from source")
                return ""
                
            return cleaned_text

        except Exception as e:
            logger.error(f"Error extracting content: {str(e)}")
            raise

def main():
    """Test the UnifiedExtractor class."""
    extractor = UnifiedExtractor()
    
    # Test URLs for different file types
    test_urls = [
        "https://calibre-ebook.com/downloads/demos/demo.docx",
        "https://www.cmu.edu/blackboard/files/evaluate/tests-example.xls",
        "https://scholar.harvard.edu/files/torman_personal/files/samplepptx.pptx",
        "https://www.w3.org/TR/2003/REC-PNG-20031110/iso_8859-1.txt",
        "https://example.com/sample.pdf",
        "https://example.com/image.jpg",
        "https://example.com/audio.mp3",
        "https://example.com/data.json",
        "https://example.com/archive.zip"
    ]
    
    for url in test_urls:
        try:
            print(f"\nTesting URL: {url}")
            content = extractor.extract_content(url)
            print("Content extracted successfully:")
            print(content[:500] + "..." if len(content) > 500 else content)
        except Exception as e:
            print(f"Error processing {url}: {str(e)}")

if __name__ == "__main__":
    main() 