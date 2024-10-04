import unittest
from unittest.mock import patch, MagicMock
from podcastfy.content_generator import ContentGenerator, main
from podcastfy.utils.config import Config


class TestGenAIPodcast(unittest.TestCase):
    def setUp(self):
        """
        Set up the test environment.
        """
        config = Config()
        self.api_key = config.GEMINI_API_KEY
        self.content_generator = ContentGenerator(self.api_key)

    def test_generate_qa_content(self):
        """
        Test the generate_qa_content method of ContentGenerator.
        """
        input_text = "United States of America"
        result = self.content_generator.generate_qa_content(input_text)
        print(result)
        self.assertIsNotNone(result)
        self.assertNotEqual(result, "")
        self.assertIsInstance(result, str)
        self.assertRegex(
            result, r"(<Person1>.*?</Person1>\s*<Person2>.*?</Person2>\s*)+"
        )


if __name__ == "__main__":
    unittest.main()
