import os
import pytest
import tempfile
from podcastfy.client import generate_podcast
from podcastfy.utils.config import load_config
from podcastfy.utils.config_conversation import load_conversation_config


@pytest.fixture
def sample_config():
    config = load_config()
    config.configure(
        output_directories={
            "audio": "tests/data/audio",
            "transcripts": "tests/data/transcripts",
        }
    )
    return config


@pytest.fixture
def sample_conversation_config():
    conversation_config = {
        "word_count": 300,
        "conversation_style": ["formal", "educational"],
        "roles_person1": "professor",
        "roles_person2": "student",
        "dialogue_structure": [
            "Introduction",
            "Main Points",
            "Case Studies",
            "Quiz",
            "Conclusion",
        ],
        "podcast_name": "Teachfy",
        "podcast_tagline": "Learning Through Conversation",
        "output_language": "English",
        "engagement_techniques": ["examples", "questions"],
        "creativity": 0,
    }
    return conversation_config


def test_generate_podcast_from_urls(sample_config):
    """Test generating a podcast from a list of URLs."""
    urls = [
        "https://en.wikipedia.org/wiki/Podcast",
        "https://en.wikipedia.org/wiki/Text-to-speech",
    ]

    audio_file = generate_podcast(urls=urls, config=sample_config)

    assert audio_file is not None
    assert os.path.exists(audio_file)
    assert audio_file.endswith(".mp3")
    assert os.path.dirname(audio_file) == sample_config.get(
        "output_directories", {}
    ).get("audio")


def test_generate_transcript_only(sample_config):
    """Test generating only a transcript without audio."""
    urls = ["https://en.wikipedia.org/wiki/Natural_language_processing"]

    result = generate_podcast(urls=urls, transcript_only=True, config=sample_config)

    assert result is None


def test_generate_podcast_from_transcript_file(sample_config):
    """Test generating a podcast from an existing transcript file."""
    # First, generate a transcript
    transcript_file = os.path.join(
        sample_config.get("output_directories", {}).get("transcripts"),
        "test_transcript.txt",
    )
    with open(transcript_file, "w") as f:
        f.write(
            "<Person1>Joe Biden and the US Politics<Person1><Person2>Joe Biden is the current president of the United States of America<Person2>"
        )

    # Now use this transcript to generate a podcast
    audio_file = generate_podcast(transcript_file=transcript_file, config=sample_config)

    assert audio_file is not None
    assert os.path.exists(audio_file)
    assert audio_file.endswith(".mp3")
    assert os.path.dirname(audio_file) == sample_config.get(
        "output_directories", {}
    ).get("audio")


def test_generate_podcast_with_custom_config(sample_config, sample_conversation_config):
    """Test generating a podcast with a custom conversation config."""
    urls = ["https://en.wikipedia.org/wiki/Artificial_intelligence"]

    audio_file = generate_podcast(
        urls=urls, config=sample_config, conversation_config=sample_conversation_config
    )

    assert audio_file is not None
    assert os.path.exists(audio_file)
    assert audio_file.endswith(".mp3")
    assert os.path.dirname(audio_file) == sample_config.get(
        "output_directories", {}
    ).get("audio")


def test_generate_podcast_no_urls_or_transcript():
    """Test that an error is raised when no URLs or transcript file is provided."""
    with pytest.raises(ValueError):
        generate_podcast()


if __name__ == "__main__":
    pytest.main()
