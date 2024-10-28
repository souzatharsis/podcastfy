import unittest
import pytest
import os
import re
from podcastfy.utils.config import load_config
from podcastfy.content_parser.content_extractor import ContentExtractor
from podcastfy.content_parser.youtube_transcriber import YouTubeTranscriber
from podcastfy.content_parser.website_extractor import WebsiteExtractor
from podcastfy.content_parser.pdf_extractor import PDFExtractor
from podcastfy.content_parser.markdown_extractor import MarkdownExtractor
import logging
logger = logging.getLogger(__name__)


class TestContentParser(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.dirname(os.path.abspath(__file__))
        self.sample_md_path = os.path.join(self.test_dir, 'data', 'sample.md')

    def test_content_extractor(self):
        # Add tests for ContentExtractor
        pass

    @pytest.mark.skip(reason="IP getting blocked by YouTube when running from GitHub Actions")
    def test_youtube_transcriber(self):
        """
        Test the YouTubeTranscriber class to ensure it correctly extracts and cleans transcripts from a YouTube video.
        """
        # Initialize YouTubeTranscriber
        transcriber = YouTubeTranscriber()

        # Test URL
        test_url = "https://www.youtube.com/watch?v=m3kJo5kEzTQ"

        # Extract transcript
        extracted_transcript = transcriber.extract_transcript(test_url)

        # Load expected transcript from youtube.txt file
        with open("./tests/data/mock/youtube.txt", "r") as f:
            expected_transcript = f.read()

        # Assert that the first 100 characters of the extracted transcript match the expected transcript
        self.assertEqual(
            extracted_transcript[:100].strip(), expected_transcript[:100].strip()
        )

    def test_website_extractor(self):
        """
        Test the WebsiteExtractor class to ensure it correctly extracts content from a website.
        """
        # pass #TODO remove pass when testing. Keeping it here to avoid running out of quota.

        # Initialize WebsiteExtractor
        config = load_config()
        extractor = WebsiteExtractor()

        # Test URL
        test_url = "http://www.souzatharsis.com"

        # Extract content
        extracted_content = extractor.extract_content(test_url)
        print(extracted_content.strip())
        # Load expected content from website.md file
        with open("./tests/data/mock/website.md", "r", encoding="utf-8") as f:
            
            expected_content = f.read()
        print(expected_content.strip())
        # Assert that the extracted content matches the expected content
        self.assertEqual(extracted_content.strip(), expected_content.strip())

    def test_pdf_extractor(self):
        """
        Test the PDFExtractor class to ensure it correctly extracts content from a PDF file.
        """
        # Initialize PDFExtractor
        extractor = PDFExtractor()

        # Path to the test PDF file
        pdf_path = "./tests/data/pdf/file.pdf"

        # Extract content from PDF
        extracted_content = extractor.extract_content(pdf_path)

        # Load expected content from file.txt
        with open("./tests/data/mock/file.txt", "r", encoding="utf-8") as f:
            expected_content = f.read()

        # Assert that the first 500 characters of the extracted content match the expected content
        self.assertEqual(
            extracted_content[:500].strip(), expected_content[:500].strip()
        )

    def test_markdown_extractor(self):
        """
        Test the MarkdownExtractor class to ensure it correctly extracts content from a Markdown file.
        """
        # Initialize MarkdownExtractor
        extractor = MarkdownExtractor()

        # Test Case 1: Using markdown.md
        # {{ Change the path to be absolute based on self.test_dir }}
        md_path = os.path.join(self.test_dir, 'data', 'markdown', 'markdown.md')
        extracted_content = extractor.extract_content(md_path)

        # Load expected content from file.md
        # {{ Change the path to be absolute based on self.test_dir }}
        with open(os.path.join(self.test_dir, 'data', 'mock', 'file.md'), "r", encoding="utf-8") as f:
            expected_content = f.read()

        # Normalize strings by removing extra whitespace and normalizing line endings
        def normalize_text(text):
            # Replace multiple newlines with single newline
            text = re.sub(r'\n+', '\n', text)
            # Remove any trailing/leading whitespace
            text = text.strip()
            return text

        normalized_extracted = normalize_text(extracted_content[:500])
        normalized_expected = normalize_text(expected_content[:500])

        # Print debug info
        print("\nExtracted content (normalized):")
        print(normalized_extracted)
        print("\nExpected content (normalized):")
        print(normalized_expected)

        # Assert that the normalized contents match
        self.assertEqual(
            normalized_extracted,
            normalized_expected,
            "Content from markdown.md does not match expected content from file.md"
        )

    def tearDown(self):
        """
        Clean up only generated test files while preserving test data and directories.
        """
        # Clean up only generated files
        test_files = [
            self.sample_md_path,  # temporary sample file
            os.path.join(self.test_dir, 'data', 'empty.md'),  # temporary empty file
        ]

        # Remove only generated files if they exist
        for file_path in test_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Cleaned up generated file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up {file_path}: {str(e)}")

        # Clean up generated files in audio and transcripts directories
        generated_dirs = [
            os.path.join(self.test_dir, 'data', 'audio'),
            os.path.join(self.test_dir, 'data', 'transcripts')
        ]

        for dir_path in generated_dirs:
            if os.path.exists(dir_path):
                try:
                    # Remove only generated files, keep the directory
                    for file_name in os.listdir(dir_path):
                        file_path = os.path.join(dir_path, file_name)
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            logger.info(f"Cleaned up generated file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up files in {dir_path}: {str(e)}")

if __name__ == "__main__":
    unittest.main()
