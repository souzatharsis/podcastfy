"""
Text File Extractor Module

This module provides functionality to extract content from text files,
supporting both local and web-hosted text files with various encodings.
"""

import logging
import requests
import chardet
from typing import Union
from urllib.parse import urlparse
import codecs

logger = logging.getLogger(__name__)

class TextExtractor:
    def __init__(self):
        """Initialize the TextExtractor."""
        self.common_encodings = [
            'utf-8', 'utf-8-sig',  # UTF-8 with and without BOM
            'utf-16', 'utf-16le', 'utf-16be',  # UTF-16 variants
            'ascii',  # ASCII
            'iso-8859-1', 'windows-1252',  # Common Western encodings
            'cp437'  # DOS/IBM encoding
        ]

    def _download_text(self, url: str) -> bytes:
        """
        Download text content from a URL.

        Args:
            url (str): The URL of the text file.

        Returns:
            bytes: The downloaded content.

        Raises:
            requests.exceptions.RequestException: If download fails.
        """
        try:
            response = requests.get(url, verify=True)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Error downloading text from {url}: {str(e)}")
            raise

    def _is_url(self, source: str) -> bool:
        """Check if the source is a URL."""
        try:
            result = urlparse(source)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False

    def _detect_encoding(self, content: bytes) -> str:
        """
        Detect the encoding of text content.

        Args:
            content (bytes): The content to analyze.

        Returns:
            str: The detected encoding.
        """
        # First try chardet
        detected = chardet.detect(content)
        if detected and detected['confidence'] > 0.7:
            return detected['encoding']

        # Try common encodings
        for encoding in self.common_encodings:
            try:
                content.decode(encoding)
                return encoding
            except UnicodeDecodeError:
                continue

        # Default to UTF-8 if nothing else works
        return 'utf-8'

    def extract_content(self, source: Union[str, bytes]) -> str:
        """
        Extract text content from a text file, handling various encodings.
        Supports both local files and web URLs.

        Args:
            source (Union[str, bytes]): Path to text file, URL, or bytes content.

        Returns:
            str: Extracted text content.

        Raises:
            UnicodeDecodeError: If the text cannot be decoded with any supported encoding.
            Exception: For other extraction errors.
        """
        try:
            if isinstance(source, bytes):
                content = source
            elif isinstance(source, str):
                if self._is_url(source):
                    content = self._download_text(source)
                else:
                    # Try to read the local file with different encodings
                    for encoding in self.common_encodings:
                        try:
                            with codecs.open(source, 'r', encoding=encoding) as f:
                                return f.read()
                        except UnicodeDecodeError:
                            continue
                    # If none of the common encodings work, try binary read and detect
                    with open(source, 'rb') as f:
                        content = f.read()
            else:
                raise ValueError("Source must be either string (path/URL) or bytes")

            # Detect encoding of the content
            encoding = self._detect_encoding(content)
            
            # Decode the content
            text = content.decode(encoding)
            
            # Clean up the text
            text = text.replace('\r\n', '\n')  # Normalize line endings
            text = text.strip()  # Remove leading/trailing whitespace
            
            if not text:
                logger.warning("Extracted text is empty")
                return ""
                
            return text

        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading text file: {str(e)}")
            raise
        except UnicodeDecodeError as e:
            logger.error(f"Error decoding text content: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error extracting text content: {str(e)}")
            raise

def main():
    """Test the TextExtractor class."""
    extractor = TextExtractor()
    
    # Test URLs
    test_urls = [
        "https://example-files.online-convert.com/document/txt/example.txt",
        "https://www.w3.org/TR/2003/REC-PNG-20031110/iso_8859-1.txt"
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