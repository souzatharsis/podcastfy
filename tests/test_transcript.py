import pytest
from podcastfy.core.transcript import TranscriptSegment, Transcript, Character
from unittest.mock import patch, mock_open

@pytest.fixture
def characters():
    character1 = Character("Person1", "John Doe", {})
    character2 = Character("Person2", "Jane Smith", {})
    return {"Person1": character1, "Person2": character2}

def test_clean_markups():
    input_text = "<speak>Hello <unsupported>World</unsupported><prosody rate='slow'>. This is a test</prosody></speak>"
    expected_output = "<speak>Hello World. This is a test</speak>"
    assert TranscriptSegment._clean_markups(input_text) == expected_output

def test_clean_markups_with_scratchpad():
    input_text = "Hello (scratchpad)<prosody pitch='high'>World</prosody>"
    expected_output = "Hello World"
    assert TranscriptSegment._clean_markups(input_text) == expected_output

def test_transcript_segment_init(characters):
    segment = TranscriptSegment("Hello <unsupported>World </unsupported><prosody volume='loud'>Test</prosody>", characters["Person1"])
    assert segment.text == "Hello World Test"
    assert segment.speaker == characters["Person1"]

def test_transcript_segment_to_dict(characters):
    segment = TranscriptSegment("Hello World", characters["Person1"], {"voice_id": "test_voice"})
    expected_dict = {
        "text": "Hello World",
        "speaker": "Person1",
        "tts_args": {"voice_id": "test_voice"}
    }
    assert segment.to_dict() == expected_dict

def test_transcript_segment_from_dict(characters):
    data = {
        "text": "Hello World",
        "speaker": "Person1",
        "tts_args": {"voice_id": "test_voice"}
    }
    segment = TranscriptSegment.from_dict(data, characters)
    assert segment.text == "Hello World"
    assert segment.speaker == characters["Person1"]
    assert segment.tts_args == {"voice_id": "test_voice"}

def test_transcript_init(characters):
    segments = [
        TranscriptSegment("Hello", characters["Person1"]),
        TranscriptSegment("Hi there", characters["Person2"])
    ]
    transcript = Transcript(segments, {"title": "Test Transcript"})
    assert len(transcript.segments) == 2
    assert transcript.metadata == {"title": "Test Transcript"}

def test_transcript_to_dict(characters):
    segments = [
        TranscriptSegment("Hello", characters["Person1"]),
        TranscriptSegment("Hi there", characters["Person2"])
    ]
    transcript = Transcript(segments, {"title": "Test Transcript"})
    expected_dict = {
        "segments": [
            {"text": "Hello", "speaker": "Person1", "tts_args": {}},
            {"text": "Hi there", "speaker": "Person2", "tts_args": {}}
        ],
        "metadata": {"title": "Test Transcript"}
    }
    assert transcript.to_dict() == expected_dict

@pytest.mark.parametrize("file_content,expected_segments", [
    ('{"segments": [{"text": "Hello", "speaker": "Person1", "tts_args": {}}], "metadata": {}}', 1),
    ('<Person1>Hello</Person1>\n<Person2>Hi there</Person2>', 2)
])
def test_transcript_load(file_content, expected_segments, characters):
    with patch('builtins.open', new_callable=mock_open, read_data=file_content):
        transcript = Transcript.load("fake_path.json", characters)
        assert len(transcript.segments) == expected_segments
        assert transcript.segments[0].speaker == characters["Person1"]

def test_transcript_str(characters):
    segments = [
        TranscriptSegment("Hello", characters["Person1"]),
        TranscriptSegment("Hi there", characters["Person2"])
    ]
    transcript = Transcript(segments, {"title": "Test Transcript"})
    expected_str = "<Person1>Hello</Person1>\n<Person2>Hi there</Person2>"
    assert str(transcript) == expected_str