"""
Content Extractor Module

This module provides functionality to extract content from various sources including
websites, YouTube videos, PDF files, and Microsoft Office documents. It serves as a
central hub for content extraction, delegating to specialized extractors based on
the source type.
"""

import logging
import re
from typing import List, Union
from urllib.parse import urlparse
from .youtube_transcriber import YouTubeTranscriber
from .website_extractor import WebsiteExtractor
from .unified_extractor import UnifiedExtractor
from podcastfy.utils.config import load_config

logger = logging.getLogger(__name__)

class ContentExtractor:
    def __init__(self):
        """
        Initialize the ContentExtractor with specialized extractors for different content types.
        """
        self.youtube_transcriber = YouTubeTranscriber()
        self.website_extractor = WebsiteExtractor()
        self.unified_extractor = UnifiedExtractor()
        self.config = load_config()
        self.content_extractor_config = self.config.get('content_extractor', {})

    def is_url(self, source: str) -> bool:
        """
        Check if the given source is a valid URL using strict validation.

        Args:
            source (str): The source to check.

        Returns:
            bool: True if the source is a valid URL, False otherwise.
        """
        if not source or not isinstance(source, str):
            return False

        # URL pattern for validation
        url_pattern = re.compile(
            r'^(?:http|ftp)s?://'  # http:// or https:// or ftp:// or ftps://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or IP
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        # For URLs with protocol
        if url_pattern.match(source):
            return True

        # For domain-only URLs (e.g., example.com)
        if '.' in source and ' ' not in source and not source.startswith('//'):
            # Check if it's a valid domain pattern
            domain_pattern = re.compile(
                r'^(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}(?:/?|[/?]\S+)?$',
                re.IGNORECASE
            )
            return bool(domain_pattern.match(source))

        return False

    def extract_content(self, source: Union[str, bytes]) -> str:
        """
        Extract content from various sources.

        Args:
            source (Union[str, bytes]): URL, file path, or bytes content of the source.

        Returns:
            str: Extracted text content.

        Raises:
            ValueError: If the source type is unsupported or invalid.
            Exception: For other extraction errors.
        """
        try:
            source_lower = source.lower() if isinstance(source, str) else ""
            
            # Handle YouTube URLs
            if isinstance(source, str) and self.is_url(source):
                # Check if it's a YouTube URL
                if any(pattern in source_lower for pattern in self.content_extractor_config['youtube_url_patterns']):
                    return self.youtube_transcriber.extract_transcript(source)
                
                # Check if it's a general website without specific file extension
                if not any(ext in source_lower for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.json', '.xml', '.csv']):
                    return self.website_extractor.extract_content(source)

            # Use UnifiedExtractor for all other content types
            return self.unified_extractor.extract_content(source)

        except Exception as e:
            logger.error(f"Error extracting content from {source}: {str(e)}")
            raise