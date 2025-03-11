import unittest
import pytest
import os
from podcastfy.text_to_speech import TextToSpeech
from podcastfy.utils.config_conversation import load_conversation_config


class TestAudio(unittest.TestCase):
    """Test suite for TextToSpeech functionality with various models.

    This class contains unit tests for the `TextToSpeech` class, ensuring the text-to-speech conversion is performed correctly with different models. It verifies the creation of audio files from text input and checks the existence and size of the generated files.

    Attributes:
        test_text (str): Sample text used for speech conversion tests.
        output_dir (str): Directory where test audio files are stored.

    Methods:
        setUp(): Prepares the environment for audio tests by setting up test text and ensuring the output directory exists.
        test_text_to_speech_openai(): Tests the OpenAI model for text-to-speech conversion.
        test_text_to_speech_elevenlabs(): Tests the ElevenLabs model for text-to-speech conversion.
        test_text_to_speech_edge(): Tests the Edge model for text-to-speech conversion.
        test_text_to_speech_google(): Tests the Google Gemini model for text-to-speech conversion.
        test_text_to_speech_google_multi(): Tests the Google Gemini Multi model for text-to-speech conversion."""
    def setUp(self):
        """Prepares the test environment for audio-related tests.

    Initializes test data and ensures the output directory exists for storing
    audio files generated during tests.

    Attributes:
        test_text (str): Sample text containing dialogues between two persons.
        output_dir (str): Directory path for output audio files."""
        self.test_text = "<Person1>Hello, how are you?</Person1><Person2>I'm doing great, thanks for asking!</Person2>"
        self.output_dir = "tests/data/audio"
        os.makedirs(self.output_dir, exist_ok=True)

    @pytest.mark.skip(reason="Testing edge only on Github Action as it's free")
    def test_text_to_speech_openai(self):
        """Test the TextToSpeech conversion using the OpenAI model.

    This test verifies that the TextToSpeech class can successfully convert
    input text to speech using the OpenAI model and produce an audio file
    with a size greater than 1 KB. The test is only performed on GitHub
    Actions due to resource considerations.

    Args:
        self: The instance of the test case.

    Returns:
        None"""
        tts = TextToSpeech(model="openai")
        output_file = os.path.join(self.output_dir, "test_openai.mp3")
        tts.convert_to_speech(self.test_text, output_file)

        self.assertTrue(os.path.exists(output_file))
        self.assertGreater(os.path.getsize(output_file), 1024)

        # Clean up
        os.remove(output_file)

    @pytest.mark.skip(reason="Testing edge only on Github Action as it's free")
    def test_text_to_speech_elevenlabs(self):
        """Test the TextToSpeech conversion using the ElevenLabs model.

    This test checks that the TextToSpeech class can successfully convert
    the given text to speech and save it as an MP3 file using the ElevenLabs model.
    It verifies that the output file is created and has a size greater than 1KB.

    Args:
        self: The instance of the test class containing test parameters,
              such as `test_text` and `output_dir`.

    Returns:
        None"""
        tts = TextToSpeech(model="elevenlabs")
        output_file = os.path.join(self.output_dir, "test_elevenlabs.mp3")
        tts.convert_to_speech(self.test_text, output_file)

        self.assertTrue(os.path.exists(output_file))
        self.assertGreater(os.path.getsize(output_file), 1024)

        # Clean up
        os.remove(output_file)

    def test_text_to_speech_edge(self):
        """Test the TextToSpeech conversion using the 'edge' model.

    This test verifies that the TextToSpeech class can successfully convert
    text into speech using the 'edge' model. It checks that the output file
    is created and is larger than 1KB, indicating that audio data is present.

    Args:
        self: Instance of the test class containing the test text and output directory.

    Returns:
        None"""
        tts = TextToSpeech(model="edge")
        output_file = os.path.join(self.output_dir, "test_edge.mp3")
        tts.convert_to_speech(self.test_text, output_file)

        self.assertTrue(os.path.exists(output_file))
        self.assertGreater(os.path.getsize(output_file), 1024)

        # Clean up
        os.remove(output_file)

    @pytest.mark.skip(reason="Testing edge only on Github Action as it's free")
    def test_text_to_speech_google(self):
        """Tests the TextToSpeech conversion using the Google model.

    This test verifies that the TextToSpeech module can convert given text
    into a speech file using the "gemini" model and that the output file
    is created and is of a minimum size.

    Args:
        self: An instance of the test class containing test configuration, 
              including the text to convert and the output directory.
    
    Returns:
        None"""
        tts = TextToSpeech(model="gemini")
        output_file = os.path.join(self.output_dir, "test_google.mp3")
        tts.convert_to_speech(self.test_text, output_file)

        self.assertTrue(os.path.exists(output_file))
        self.assertGreater(os.path.getsize(output_file), 1024)

        # Clean up
        os.remove(output_file)

    @pytest.mark.skip(reason="Testing edge only on Github Action as it's free")
    def test_text_to_speech_google_multi(self):
        """Tests the functionality of converting text to speech using the 'gemini_multi' model.

    This test verifies that the TextToSpeech class can convert text to speech and save
    the output as an MP3 file. It checks that the output file is created and is larger
    than 1KB to ensure content has been generated. The test is intended to run on
    Github Action due to its resource requirements.

    Args:
        self: An instance of the test case class containing test configurations and 
              resources such as test_text and output_dir.

    Returns:
        None"""
        tts = TextToSpeech(model="gemini_multi")
        output_file = os.path.join(self.output_dir, "test_google_multi.mp3")
        tts.convert_to_speech(self.test_text, output_file)

        self.assertTrue(os.path.exists(output_file))
        self.assertGreater(os.path.getsize(output_file), 1024)

        # Clean up
        os.remove(output_file)


if __name__ == "__main__":
    unittest.main()
