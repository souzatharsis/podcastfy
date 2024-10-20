"""
Unit tests for the Podcastfy CLI client.
"""

import os
import pytest
import re
from typer.testing import CliRunner
from podcastfy.client import app
from podcastfy.utils.config import load_config

runner = CliRunner()

# Mock data
MOCK_URLS = [
	"https://en.wikipedia.org/wiki/Podcast",
	"https://en.wikipedia.org/wiki/Text-to-speech"
]
MOCK_FILE_CONTENT = "\n".join(MOCK_URLS)
MOCK_TRANSCRIPT = "<Person1>Joe Biden and the US Politics</Person1><Person2>Joe Biden is the current president of the United States of America</Person2>"
MOCK_IMAGE_PATHS = [
	"tests/data/images/Senecio.jpeg",
	"tests/data/images/connection.jpg"
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
		"config_file": str(config_file)
	}

@pytest.fixture
def sample_config():
	config = load_config()
	config.configure(
		output_directories={
			'audio': 'tests/data/audio',
			'transcripts': 'tests/data/transcripts'
		}
	)
	return config

def test_generate_podcast_from_urls(sample_config):
	result = runner.invoke(app, ["--url", MOCK_URLS[0], "--url", MOCK_URLS[1], "--tts-model", "edge"])
	assert result.exit_code == 0
	assert "Podcast generated successfully using edge TTS model" in result.stdout
	assert os.path.exists(result.stdout.split(": ")[-1].strip())
	assert result.stdout.split(": ")[-1].strip().endswith('.mp3')

def test_generate_podcast_from_file(mock_files, sample_config):
	result = runner.invoke(app, ["--file", mock_files["url_file"], "--tts-model", "edge"])
	assert result.exit_code == 0
	assert "Podcast generated successfully using edge TTS model" in result.stdout
	assert os.path.exists(result.stdout.split(": ")[-1].strip())
	assert result.stdout.split(": ")[-1].strip().endswith('.mp3')

def test_generate_podcast_from_transcript(mock_files, sample_config):
	result = runner.invoke(app, ["--transcript", mock_files["transcript_file"], "--tts-model", "edge"])
	assert result.exit_code == 0
	assert "Podcast generated successfully using edge TTS model" in result.stdout
	assert os.path.exists(result.stdout.split(": ")[-1].strip())
	assert result.stdout.split(": ")[-1].strip().endswith('.mp3')

def test_generate_transcript_only(sample_config):
	result = runner.invoke(app, ["--url", MOCK_URLS[0], "--transcript-only"])
	assert result.exit_code == 0
	assert "Transcript generated successfully" in result.stdout
	
	# Extract the transcript path
	transcript_path = result.stdout.split(": ")[-1].strip()
	
	assert transcript_path, "Transcript path is empty"
	assert os.path.exists(transcript_path), f"Transcript file does not exist at path: {transcript_path}"
	
	with open(transcript_path, 'r') as f:
		content = f.read()
		assert content != ""
		assert isinstance(content, str)
		assert all("<Person1>" in tag and "</Person1>" in tag for tag in re.findall(r"<Person1>.*?</Person1>", content))
		assert all("<Person2>" in tag and "</Person2>" in tag for tag in re.findall(r"<Person2>.*?</Person2>", content))

def test_generate_podcast_from_urls_and_file(mock_files, sample_config):
	result = runner.invoke(app, ["--url", MOCK_URLS[0], "--file", mock_files["url_file"], "--tts-model", "edge"])
	assert result.exit_code == 0
	assert "Podcast generated successfully using edge TTS model" in result.stdout
	assert os.path.exists(result.stdout.split(": ")[-1].strip())
	assert result.stdout.split(": ")[-1].strip().endswith('.mp3')

def test_generate_podcast_from_image(sample_config):
	result = runner.invoke(app, ["--image", MOCK_IMAGE_PATHS[0], "--tts-model", "edge"])
	assert result.exit_code == 0
	assert "Podcast generated successfully using edge TTS model" in result.stdout
	assert os.path.exists(result.stdout.split(": ")[-1].strip())
	assert result.stdout.split(": ")[-1].strip().endswith('.mp3')

@pytest.mark.skip(reason="To be further tested")
def test_generate_podcast_with_custom_config(mock_files, sample_config):
	result = runner.invoke(app, [
		"--url", MOCK_URLS[0],
		"--conversation-config", mock_files["config_file"],
		"--tts-model", "edge"
	])
	assert result.exit_code == 0
	assert "Podcast generated successfully using edge TTS model" in result.stdout
	audio_path = result.stdout.split(": ")[-1].strip()
	assert os.path.exists(audio_path)
	assert audio_path.endswith('.mp3')
	
	# Check for elements from the custom config in the transcript
	transcript_path = audio_path.replace('.mp3', '.txt')
	assert os.path.exists(transcript_path)
	with open(transcript_path, 'r') as f:
		content = f.read()
		assert "Teachfy" in content
		assert "Learning Through Conversation" in content

def test_generate_podcast_from_urls_and_images(sample_config):
	result = runner.invoke(app, ["--url", MOCK_URLS[0], "--image", MOCK_IMAGE_PATHS[0], "--tts-model", "edge"])
	assert result.exit_code == 0
	assert "Podcast generated successfully using edge TTS model" in result.stdout
	assert os.path.exists(result.stdout.split(": ")[-1].strip())
	assert result.stdout.split(": ")[-1].strip().endswith('.mp3')


@pytest.mark.skip(reason="Requires local LLM running")
def test_generate_transcript_with_local_llm(sample_config):
	result = runner.invoke(app, ["--url", MOCK_URLS[0], "--transcript-only", "--local", "--tts-model", "edge"])
	assert result.exit_code == 0
	assert "Transcript generated successfully" in result.stdout
	transcript_path = result.stdout.split(": ")[-1].strip()
	assert os.path.exists(transcript_path)
	with open(transcript_path, 'r') as f:
		content = f.read()
		assert content != ""
		assert isinstance(content, str)
		assert re.match(r"(<Person1>.*?</Person1>\s*<Person2>.*?</Person2>\s*)+", content)

def test_cli_help():
	result = runner.invoke(app, ["--help"])
	assert result.exit_code == 0
	assert "Generate a podcast or transcript from a list of URLs" in result.stdout

def test_no_input_provided():
	result = runner.invoke(app)
	assert result.exit_code != 0
	assert "No input provided" in result.stdout

if __name__ == "__main__":
	pytest.main()
