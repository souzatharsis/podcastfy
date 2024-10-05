import os
import pytest
from podcastfy.client import generate_podcast
from podcastfy.utils.config import load_config

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
	"""Test generating a podcast from a list of URLs."""
	urls = [
		"https://en.wikipedia.org/wiki/Podcast",
		"https://en.wikipedia.org/wiki/Text-to-speech"
	]
	

	result = generate_podcast(
		urls=urls,
		config=sample_config
	)

	assert os.path.exists(result)
	assert result.endswith('.mp3')
	assert os.path.dirname(result) == sample_config.get('output_directories', {}).get('audio')

def test_generate_transcript_only(sample_config):
	"""Test generating only a transcript without audio."""
	urls = ["https://en.wikipedia.org/wiki/Natural_language_processing"]
	
	result = generate_podcast(
		urls=urls,
		transcript_only=True,
		config=sample_config
	)
	
	assert os.path.exists(result)
	assert result.endswith('.txt')
	assert os.path.dirname(result) == sample_config.get('output_directories', {}).get('transcripts')

def test_generate_podcast_from_transcript_file(sample_config):
	"""Test generating a podcast from an existing transcript file."""
	# First, generate a transcript
	transcript_result = generate_podcast(
		urls=["https://en.wikipedia.org/wiki/Artificial_intelligence"],
		transcript_only=True,
		config=sample_config
	)
	
	# Now use this transcript to generate a podcast
	result = generate_podcast(
		transcript_file=transcript_result,
		config=sample_config
	)
	
	assert os.path.exists(result)
	assert result.endswith('.mp3')
	# This assertion checks if the directory of the generated podcast file
	# matches the 'audio' output directory specified in the sample configuration.
	# It ensures that the podcast is saved in the correct location.
	assert os.path.dirname(result) == sample_config.get('output_directories', {}).get('audio')

def test_generate_podcast_no_urls_or_transcript():
	"""Test that an error is raised when no URLs or transcript file is provided."""
	with pytest.raises(ValueError):
		generate_podcast()

if __name__ == "__main__":
	pytest.main()