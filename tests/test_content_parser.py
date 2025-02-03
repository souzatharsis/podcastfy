"""
Test Content Parser Module

This module contains comprehensive tests for content extraction functionality,
including edge cases and error handling for various file types.
"""

import os
import unittest
import pytest
import tempfile
import requests
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO
import pandas as pd

from podcastfy.utils.config import load_config
from podcastfy.content_parser.content_extractor import ContentExtractor
from podcastfy.content_parser.youtube_transcriber import YouTubeTranscriber
from podcastfy.content_parser.website_extractor import WebsiteExtractor
from podcastfy.content_parser.unified_extractor import UnifiedExtractor

# Test data URLs
TEST_URLS = {
    'pdf': 'https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf',
    'docx': 'https://calibre-ebook.com/downloads/demos/demo.docx',
    'excel': 'https://file-examples.com/wp-content/storage/2017/02/file_example_XLS_10.xls',
    'pptx': 'https://scholar.harvard.edu/files/torman_personal/files/samplepptx.pptx',
    'website': 'https://example.com',
    'youtube': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
    'text': 'https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.txt',
    'text_iso': 'https://www.w3.org/TR/2003/REC-PNG-20031110/iso_8859-1.txt'
}

def create_mock_response(content: bytes, status_code: int = 200):
    """Create a mock requests.Response object."""
    mock_response = Mock(spec=requests.Response)
    mock_response.content = content
    mock_response.status_code = status_code
    mock_response.raise_for_status = Mock()
    if status_code >= 400:
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
    mock_response.text = content.decode() if isinstance(content, bytes) else content
    return mock_response

class TestContentParser(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = {
            'content_extractor': {
                'youtube_url_patterns': ['youtube.com/watch', 'youtu.be/']
            },
            'website_extractor': {
                'unwanted_tags': ['script', 'style', 'nav', 'header', 'footer'],
                'markdown_cleaning': {
                    'remove_patterns': [
                        r'\[.*?\]',
                        r'\(.*?\)',
                        r'^\s*[-*]\s',
                        r'^\s*\d+\.\s',
                        r'^\s*#+'
                    ]
                }
            },
            'youtube_transcriber': {
                'remove_phrases': ['[music]']
            }
        }
        self.patcher = patch('podcastfy.utils.config.load_config')
        self.mock_load_config = self.patcher.start()
        self.mock_load_config.return_value = self.mock_config

    def tearDown(self):
        """Clean up test fixtures."""
        self.patcher.stop()

    @patch('youtube_transcript_api.YouTubeTranscriptApi.get_transcript')
    def test_youtube_transcriber(self, mock_get_transcript):
        """Test YouTube transcript extraction."""
        transcriber = YouTubeTranscriber()
        mock_transcript = [
            {'text': 'Hello world'},
            {'text': '[Music]'},
            {'text': 'This is a test'},
            {'text': 'End of transcript'}
        ]
        mock_get_transcript.return_value = mock_transcript
        
        transcript = transcriber.extract_transcript(TEST_URLS['youtube'])
        expected = "Hello world This is a test End of transcript"
        self.assertEqual(transcript.strip(), expected.strip())

        # Test error handling
        mock_get_transcript.side_effect = Exception("Transcript not available")
        with self.assertRaises(Exception):
            transcriber.extract_transcript(TEST_URLS['youtube'])

    @patch('requests.get')
    def test_website_extractor(self, mock_get):
        """Test website content extraction."""
        extractor = WebsiteExtractor()
        mock_html = """
        <!DOCTYPE html>
        <html><body>
            <nav>Skip this</nav>
            <header>Skip this too</header>
            <h1>Main Title</h1>
            <p>Test paragraph</p>
            <script>var x = 10;</script>
            <style>.test{color:red;}</style>
            <footer>Skip footer</footer>
        </body></html>
        """
        mock_get.return_value = create_mock_response(mock_html.encode())
        
        content = extractor.extract_content(TEST_URLS['website'])
        self.assertIn("Main Title", content)
        self.assertIn("Test paragraph", content)
        self.assertNotIn("Skip this", content)
        self.assertNotIn("var x = 10", content)
        self.assertNotIn(".test{color:red}", content)

    @patch('markitdown.MarkItDown.convert')
    def test_unified_extractor(self, mock_convert):
        """Test unified content extraction."""
        extractor = UnifiedExtractor()
        mock_result = MagicMock()
        mock_result.text_content = "Test content with some formatting"
        mock_convert.return_value = mock_result

        # Test bytes input
        content = extractor.extract_content(b'test content')
        self.assertEqual(content, "Test content with some formatting")

        # Test file URL
        with patch('requests.get') as mock_get:
            mock_get.return_value = create_mock_response(b'test content')
            content = extractor.extract_content(TEST_URLS['pdf'])
            self.assertEqual(content, "Test content with some formatting")

    def test_content_extractor(self):
        """Test content extractor routing."""
        extractor = ContentExtractor()
        
        # Test URL detection
        self.assertTrue(extractor.is_url('https://example.com'))
        self.assertTrue(extractor.is_url('http://example.com'))
        self.assertTrue(extractor.is_url('example.com'))
        self.assertFalse(extractor.is_url('not-a-url'))
        self.assertFalse(extractor.is_url(''))

        # Test content extraction routing
        with patch.object(YouTubeTranscriber, 'extract_transcript') as mock_yt:
            mock_yt.return_value = "test transcript"
            content = extractor.extract_content(TEST_URLS['youtube'])
            self.assertEqual(content, "test transcript")
            mock_yt.assert_called_once()

        with patch.object(WebsiteExtractor, 'extract_content') as mock_web:
            mock_web.return_value = "test web content"
            content = extractor.extract_content(TEST_URLS['website'])
            self.assertEqual(content, "test web content")
            mock_web.assert_called_once()

        with patch.object(UnifiedExtractor, 'extract_content') as mock_unified:
            mock_unified.return_value = "test file content"
            content = extractor.extract_content(TEST_URLS['pdf'])
            self.assertEqual(content, "test file content")
            mock_unified.assert_called_once()

if __name__ == "__main__":
    unittest.main()
