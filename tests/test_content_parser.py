import unittest
import pytest
from podcastfy.utils.config import load_config
from podcastfy.content_parser.content_extractor import ContentExtractor
from podcastfy.content_parser.youtube_transcriber import YouTubeTranscriber
from podcastfy.content_parser.website_extractor import WebsiteExtractor
from podcastfy.content_parser.pdf_extractor import PDFExtractor


class TestContentParser(unittest.TestCase):
    def test_content_extractor(self):
        # Add tests for ContentExtractor
        pass

    @pytest.mark.skip(
        reason="IP getting blocked by YouTube when running from GitHub Actions"
    )
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
        with open("./tests/data/mock/website.md", "r") as f:
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
        with open("./tests/data/mock/file.txt", "r") as f:
            expected_content = f.read()

        # Assert that the first 500 characters of the extracted content match the expected content
        self.assertEqual(
            extracted_content[:500].strip(), expected_content[:500].strip()
        )

    @pytest.mark.skip(reason="Too expensive to be auto tested on Github Actions")
    def test_generate_topic_content(self):
        """Test generating content for a specific topic."""
        extractor = ContentExtractor()
        topic = "Latest news about OpenAI"

        # Generate content for the topic
        content = extractor.generate_topic_content(topic)

        # Verify the content
        self.assertIsNotNone(content)
        self.assertIsInstance(content, str)
        self.assertGreater(len(content), 100)  # Content should be substantial

        # Check if content is relevant to the topic
        lower_content = content.lower()
        self.assertTrue(
            any(term in lower_content for term in ["openai"]),
            "Generated content should be relevant to the topic",
        )


if __name__ == "__main__":
    unittest.main()
