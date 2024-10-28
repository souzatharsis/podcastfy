import unittest
import os
import re
import logging
from podcastfy.content_parser.markdown_extractor import MarkdownExtractor

logger = logging.getLogger(__name__)

class TestMarkdownExtractor(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.dirname(os.path.abspath(__file__))
        self.sample_md_path = os.path.join(self.test_dir, 'data', 'sample.md')
        self.extractor = MarkdownExtractor()

    def test_extract_content(self):
        """
        Test the MarkdownExtractor class with actual markdown file.
        """
        # Use the same markdown file as test_content_parser.py
        md_path = os.path.join(self.test_dir, 'data', 'markdown', 'markdown.md')
        extracted_content = self.extractor.extract_content(md_path)

        # Load expected content
        with open(os.path.join(self.test_dir, 'data', 'mock', 'file.md'), "r", encoding="utf-8") as f:
            expected_content = f.read()

        # Normalize strings
        def normalize_text(text):
            text = re.sub(r'\n+', '\n', text)
            return text.strip()

        normalized_extracted = normalize_text(extracted_content[:500])
        normalized_expected = normalize_text(expected_content[:500])

        # Assert that the normalized contents match
        self.assertEqual(
            normalized_extracted,
            normalized_expected,
            "Extracted content does not match expected content"
        )

    def test_extract_content_empty_file(self):
        """Test extracting content from an empty file."""
        empty_md_path = os.path.join(self.test_dir, 'data', 'empty.md')
        with open(empty_md_path, 'w', encoding='utf-8') as f:
            f.write('')

        extracted_content = self.extractor.extract_content(empty_md_path)
        self.assertEqual(extracted_content.strip(), '')

    def test_extract_content_file_not_found(self):
        """Test handling of non-existent file."""
        non_existent_path = os.path.join(self.test_dir, 'data', 'non_existent.md')
        with self.assertRaises(Exception):
            self.extractor.extract_content(non_existent_path)

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

if __name__ == '__main__':
    unittest.main()
