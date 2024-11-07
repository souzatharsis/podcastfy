"""
Unit tests for the Podcastfy CLI client.
"""

import os
import pytest
import re
from typer.testing import CliRunner
from podcastfy.client import app

runner = CliRunner()


# Mock data
MOCK_URLS = [
    "https://en.wikipedia.org/wiki/Podcast",
    "https://en.wikipedia.org/wiki/Text-to-speech",
]
MOCK_FILE_CONTENT = "\n".join(MOCK_URLS)
MOCK_TRANSCRIPT = "<Person1>Joe Biden and the US Politics</Person1><Person2>Joe Biden is the current president of the United States of America</Person2>"
MOCK_IMAGE_PATHS = [
    "https://raw.githubusercontent.com/souzatharsis/podcastfy/refs/heads/main/data/images/Senecio.jpeg",
    "https://raw.githubusercontent.com/souzatharsis/podcastfy/refs/heads/main/data/images/connection.jpg",
]
MOCK_CONVERSATION_CONFIG = """
word_count: 300
conversation_style: 
  - formal
  - educational
roles_person1: professor
roles_person2: student
dialogue_structure: 
  - Introduction
  - Main Points
  - Case Studies
  - Quiz
  - Conclusion
podcast_name: Teachfy
podcast_tagline: Learning Through Conversation
output_language: English
engagement_techniques: 
  - examples
  - questions
creativity: 0
text_to_speech:
	model: edge
"""


@pytest.fixture
def mock_files(tmp_path):
    # Create mock files
    url_file = tmp_path / "urls.txt"
    url_file.write_text(MOCK_FILE_CONTENT)

    transcript_file = tmp_path / "transcript.txt"
    transcript_file.write_text(MOCK_TRANSCRIPT)

    config_file = tmp_path / "custom_config.yaml"
    config_file.write_text(MOCK_CONVERSATION_CONFIG)

    return {
        "url_file": str(url_file),
        "transcript_file": str(transcript_file),
        "config_file": str(config_file),
    }


@pytest.fixture
def sample_config():
    """
    Fixture to provide a sample conversation configuration for testing.

    Returns:
            dict: A dictionary containing sample conversation configuration parameters.
    """
    conversation_config = {
        "word_count": 300,
        "text_to_speech": {
            "output_directories": {
                "transcripts": "tests/data/transcripts",
                "audio": "tests/data/audio",
            },
            "temp_audio_dir": "tests/data/audio/tmp",
            "ending_message": "Bye Bye!",
        },
    }
    return conversation_config


def test_generate_podcast_from_urls(sample_config):
    result = runner.invoke(
        app, ["--url", MOCK_URLS[0], "--url", MOCK_URLS[1], "--tts-model", "edge"]
    )
    assert result.exit_code == 0
    assert "Podcast generated successfully using edge TTS model" in result.stdout
    audio_path = result.stdout.split(": ")[-1].strip()
    assert os.path.exists(audio_path)
    assert audio_path.endswith(".mp3")
    assert os.path.getsize(audio_path) > 1024  # Check if larger than 1KB


def test_generate_podcast_from_file(mock_files, sample_config):
    result = runner.invoke(
        app, ["--file", mock_files["url_file"], "--tts-model", "edge"]
    )
    assert result.exit_code == 0
    assert "Podcast generated successfully using edge TTS model" in result.stdout
    assert os.path.exists(result.stdout.split(": ")[-1].strip())
    assert result.stdout.split(": ")[-1].strip().endswith(".mp3")
    assert (
        os.path.getsize(result.stdout.split(": ")[-1].strip()) > 1024
    )  # Check if larger than 1KB


def test_generate_podcast_from_transcript(mock_files, sample_config):
    result = runner.invoke(
        app, ["--transcript", mock_files["transcript_file"], "--tts-model", "edge"]
    )
    assert result.exit_code == 0
    assert "Podcast generated successfully using edge TTS model" in result.stdout
    assert os.path.exists(result.stdout.split(": ")[-1].strip())
    assert result.stdout.split(": ")[-1].strip().endswith(".mp3")
    assert (
        os.path.getsize(result.stdout.split(": ")[-1].strip()) > 1024
    )  # Check if larger than 1KB


def test_generate_transcript_only(sample_config):
    result = runner.invoke(app, ["--url", MOCK_URLS[0], "--transcript-only"])
    assert result.exit_code == 0
    assert "Transcript generated successfully" in result.stdout

    # Extract the transcript path
    transcript_path = result.stdout.split(": ")[-1].strip()

    assert transcript_path, "Transcript path is empty"
    assert os.path.exists(
        transcript_path
    ), f"Transcript file does not exist at path: {transcript_path}"

    with open(transcript_path, "r") as f:
        content = f.read()
        assert content != ""
        assert isinstance(content, str)
        assert all(
            "<Person1>" in tag and "</Person1>" in tag
            for tag in re.findall(r"<Person1>.*?</Person1>", content)
        )
        assert all(
            "<Person2>" in tag and "</Person2>" in tag
            for tag in re.findall(r"<Person2>.*?</Person2>", content)
        )


@pytest.mark.skip(reason="Not supported yet")
def test_generate_podcast_from_urls_and_file(mock_files, sample_config):
    result = runner.invoke(
        app,
        [
            "--url",
            MOCK_URLS[0],
            "--file",
            mock_files["url_file"],
            "--tts-model",
            "edge",
        ],
    )
    assert result.exit_code == 0
    assert "Podcast generated successfully using edge TTS model" in result.stdout
    assert os.path.exists(result.stdout.split(": ")[-1].strip())
    assert result.stdout.split(": ")[-1].strip().endswith(".mp3")
    assert (
        os.path.getsize(result.stdout.split(": ")[-1].strip()) > 1024
    )  # Check if larger than 1KB


def test_generate_podcast_from_image(sample_config):
    result = runner.invoke(app, ["--image", MOCK_IMAGE_PATHS[0], "--tts-model", "edge"])
    assert result.exit_code == 0
    assert "Podcast generated successfully using edge TTS model" in result.stdout
    assert os.path.exists(result.stdout.split(": ")[-1].strip())
    assert result.stdout.split(": ")[-1].strip().endswith(".mp3")
    assert (
        os.path.getsize(result.stdout.split(": ")[-1].strip()) > 1024
    )  # Check if larger than 1KB


@pytest.mark.skip(reason="To be further tested")
def test_generate_podcast_with_custom_config(mock_files, sample_config):
    result = runner.invoke(
        app,
        [
            "--url",
            MOCK_URLS[0],
            "--conversation-config",
            mock_files["config_file"],
            "--tts-model",
            "edge",
        ],
    )
    assert result.exit_code == 0
    assert "Podcast generated successfully using edge TTS model" in result.stdout
    audio_path = result.stdout.split(": ")[-1].strip()
    assert os.path.exists(audio_path)
    assert audio_path.endswith(".mp3")
    assert os.path.getsize(audio_path) > 1024  # Check if larger than 1KB

    # Check for elements from the custom config in the transcript
    transcript_path = audio_path.replace(".mp3", ".txt")
    assert os.path.exists(transcript_path)
    with open(transcript_path, "r") as f:
        content = f.read()
        assert "Teachfy" in content
        assert "Learning Through Conversation" in content


def test_generate_podcast_from_urls_and_images(sample_config):
    result = runner.invoke(
        app,
        ["--url", MOCK_URLS[0], "--image", MOCK_IMAGE_PATHS[0], "--tts-model", "edge"],
    )
    assert result.exit_code == 0
    assert "Podcast generated successfully using edge TTS model" in result.stdout
    assert os.path.exists(result.stdout.split(": ")[-1].strip())
    assert result.stdout.split(": ")[-1].strip().endswith(".mp3")
    assert (
        os.path.getsize(result.stdout.split(": ")[-1].strip()) > 1024
    )  # Check if larger than 1KB


@pytest.mark.skip(reason="Requires local LLM running")
def test_generate_transcript_with_local_llm(sample_config):
    result = runner.invoke(
        app,
        ["--url", MOCK_URLS[0], "--transcript-only", "--local", "--tts-model", "edge"],
    )
    assert result.exit_code == 0
    assert "Transcript generated successfully" in result.stdout
    transcript_path = result.stdout.split(": ")[-1].strip()
    assert os.path.exists(transcript_path)
    with open(transcript_path, "r") as f:
        content = f.read()
        assert content != ""
        assert isinstance(content, str)
        assert re.match(
            r"(<Person1>.*?</Person1>\s*<Person2>.*?</Person2>\s*)+", content
        )


def test_generate_podcast_from_raw_text():
    """Test generating a podcast from raw input text using the CLI."""
    raw_text = "The wonderful world of LLMs."
    result = runner.invoke(app, ["--text", raw_text, "--tts-model", "edge"])
    assert result.exit_code == 0
    assert "Podcast generated successfully using edge TTS model" in result.stdout
    audio_path = result.stdout.split(": ")[-1].strip()
    assert os.path.exists(audio_path)
    assert audio_path.endswith(".mp3")
    assert os.path.getsize(audio_path) > 1024  # Check if larger than 1KB


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Generate a podcast or transcript from a list of URLs" in result.stdout


def test_no_input_provided():
    result = runner.invoke(app)
    assert result.exit_code != 0
    assert "No input provided" in result.stdout


def test_generate_podcast_with_custom_llm():
    """Test generating a podcast with a custom LLM model using CLI."""
    result = runner.invoke(
        app,
        [
            "--url",
            MOCK_URLS[0],
            "--tts-model",
            "edge",
            "--llm-model-name",
            "gemini-1.5-pro-latest",
            "--api-key-label",
            "GEMINI_API_KEY",
        ],
    )

    assert result.exit_code == 0
    assert "Podcast generated successfully using edge TTS model" in result.stdout

    # Extract and verify the audio file
    audio_path = result.stdout.split(": ")[-1].strip()
    assert os.path.exists(audio_path)
    assert audio_path.endswith(".mp3")
    assert os.path.getsize(audio_path) > 1024  # Check if larger than 1KB

    # Clean up
    os.remove(audio_path)


def test_generate_transcript_only_with_custom_llm():
    """Test generating only a transcript with a custom LLM model using CLI."""
    result = runner.invoke(
        app,
        [
            "--url",
            MOCK_URLS[0],
            "--transcript-only",
            "--llm-model-name",
            "gemini-1.5-pro-latest",
            "--api-key-label",
            "GEMINI_API_KEY",
        ],
    )

    assert result.exit_code == 0
    assert "Transcript generated successfully" in result.stdout

    # Extract and verify the transcript file
    transcript_path = result.stdout.split(": ")[-1].strip()
    assert os.path.exists(transcript_path)
    assert transcript_path.endswith(".txt")

    # Verify transcript content
    with open(transcript_path, "r") as f:
        content = f.read()
        assert content != ""
        assert isinstance(content, str)
        assert "<Person1>" in content
        assert "<Person2>" in content
        assert len(content.split("<Person1>")) > 1  # At least one question
        assert len(content.split("<Person2>")) > 1  # At least one answer

        # Verify content is substantial
        min_length = 500  # Minimum expected length in characters
        assert (
            len(content) > min_length
        ), f"Content length ({len(content)}) is less than minimum expected ({min_length})"

    # Clean up
    os.remove(transcript_path)


@pytest.mark.skip(reason="Too expensive to be auto tested on Github Actions")
def test_generate_podcast_from_topic():
    """Test generating a podcast from a topic using CLI."""
    result = runner.invoke(
        app, ["--topic", "Artificial Intelligence Ethics", "--tts-model", "edge"]
    )

    assert result.exit_code == 0
    assert "Podcast generated successfully using edge TTS model" in result.stdout

    # Extract and verify the audio file
    audio_path = result.stdout.split(": ")[-1].strip()
    assert os.path.exists(audio_path)
    assert audio_path.endswith(".mp3")
    assert os.path.getsize(audio_path) > 1024  # Check if larger than 1KB

    # Clean up
    os.remove(audio_path)


if __name__ == "__main__":
    pytest.main()
