import unittest
import os
from podcastfy.content_parser.markdown_extractor import MarkdownExtractor

class TestMarkdownExtractor(unittest.TestCase):
    def setUp(self):
        self.extractor = MarkdownExtractor()
        self.test_dir = os.path.dirname(os.path.abspath(__file__))
        self.sample_md_path = os.path.join(self.test_dir, 'data', 'sample.md')

    def test_extract_content(self):
        # Create a sample markdown file
        sample_content = """# Sample Markdown

This is a paragraph.

## Subheading

- List item 1
- List item 2

[Link](https://example.com)
"""
        with open(self.sample_md_path, 'w', encoding='utf-8') as f:
            f.write(sample_content)

        # Extract content
        extracted_content = self.extractor.extract_content(self.sample_md_path)

        # Check if the extracted content matches the expected output
        expected_output = """Sample Markdown
This is a paragraph.
Subheading
List item 1
List item 2
Link"""
        self.assertEqual(extracted_content.strip().replace('\n\n', '\n'), expected_output.strip())

    def test_extract_content_empty_file(self):
        # Create an empty markdown file
        empty_md_path = os.path.join(self.test_dir, 'data', 'empty.md')
        with open(empty_md_path, 'w', encoding='utf-8') as f:
            f.write('')

        # Extract content from empty file
        extracted_content = self.extractor.extract_content(empty_md_path)

        # Check if the extracted content is empty
        self.assertEqual(extracted_content.strip(), '')

    def test_extract_content_file_not_found(self):
        # Try to extract content from a non-existent file
        non_existent_path = os.path.join(self.test_dir, 'data', 'non_existent.md')

        # Check if the correct exception is raised
        with self.assertRaises(Exception):
            self.extractor.extract_content(non_existent_path)

    def tearDown(self):
        # Clean up created files
        if os.path.exists(self.sample_md_path):
            os.remove(self.sample_md_path)
        empty_md_path = os.path.join(self.test_dir, 'data', 'empty.md')
        if os.path.exists(empty_md_path):
            os.remove(empty_md_path)

if __name__ == '__main__':
    unittest.main()
