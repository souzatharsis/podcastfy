import unittest
import pytest
from unittest.mock import patch, MagicMock
import tempfile
import os
from podcastfy.content_generator import ContentGenerator
from podcastfy.utils.config import Config
from podcastfy.utils.config_conversation import ConversationConfig
from podcastfy.content_parser.pdf_extractor import PDFExtractor


# TODO: Should be a fixture
def sample_conversation_config():
    conversation_config = {
        "word_count": 500,
        "roles_person1": "professor",
        "roles_person2": "student",
        "podcast_name": "Teachfy",
        "podcast_tagline": "Learning Through Conversation"
    }
    return conversation_config


class TestGenAIPodcast(unittest.TestCase):
    def setUp(self):
        """
        Set up the test environment.
        """
        config = Config()
        self.api_key = config.GEMINI_API_KEY
        self.config = config

    def test_generate_qa_content(self):
        """
        Test the generate_qa_content method of ContentGenerator.
        """
        content_generator = ContentGenerator(self.api_key)
        input_text = "United States of America"
        result = content_generator.generate_qa_content(input_text)
        self.assertIsNotNone(result)
        self.assertNotEqual(result, "")
        self.assertIsInstance(result, str)
        self.assertRegex(
            result, r"(<Person1>.*?</Person1>\s*<Person2>.*?</Person2>\s*)+"
        )

    def test_custom_conversation_config(self):
        """
        Test the generation of content using a custom conversation configuration file.
        """
        conversation_config = sample_conversation_config()
        content_generator = ContentGenerator(self.api_key, conversation_config)
        input_text = "United States of America"

        result = content_generator.generate_qa_content(input_text)

        self.assertIsNotNone(result)
        self.assertNotEqual(result, "")
        self.assertIsInstance(result, str)

        # Check for elements from the custom config
        self.assertIn(conversation_config["podcast_name"].lower(), result.lower())
        self.assertIn(conversation_config["podcast_tagline"].lower(), result.lower())

        # Check word count (allow some flexibility)
        word_count = len(result.split())

    def test_generate_qa_content_from_images(self):
        """Test generating Q&A content from two input images."""
        image_paths = [
            "tests/data/images/Senecio.jpeg",
            "tests/data/images/connection.jpg",
        ]

        content_generator = ContentGenerator(self.api_key)

        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".txt", delete=False
        ) as temp_file:
            result = content_generator.generate_qa_content(
                input_texts="",  # Empty string for input_texts
                image_file_paths=image_paths,
                output_filepath=temp_file.name,
            )

        self.assertIsNotNone(result)
        self.assertNotEqual(result, "")
        self.assertIsInstance(result, str)

        # Check if the output file was created and contains the same content
        with open(temp_file.name, "r") as f:
            file_content = f.read()

        self.assertEqual(result, file_content)

        # Clean up the temporary file
        os.unlink(temp_file.name)

    def test_generate_qa_content_from_pdf(self):
        """Test generating Q&A content from a PDF file."""
        pdf_file = "tests/data/pdf/file.pdf"
        content_generator = ContentGenerator(self.api_key)
        pdf_extractor = PDFExtractor()

        # Extract content from the PDF file
        extracted_content = pdf_extractor.extract_content(pdf_file)

        # Generate Q&A content from the extracted text
        result = content_generator.generate_qa_content(
            input_texts=extracted_content
        )

        self.assertIsNotNone(result)
        self.assertNotEqual(result, "")
        self.assertIsInstance(result, str)

if __name__ == "__main__":
    unittest.main()
