import json
import re
from typing import Optional, Dict, Any, List, Tuple

from podcastfy.core.character import Character



class TranscriptSegment:
    def __init__(self, text: str, speaker: Character,
                 tts_args: Optional[Dict[str, Any]] = None,
                 auto_clean_markup=True) -> None:
        self.text = self._clean_markups(text) if auto_clean_markup else text
        self.speaker = speaker
        self.tts_args = tts_args or {}

    @staticmethod
    def _clean_markups(input_text: str) -> str:
        """
        Remove unsupported TSS markup tags from the input text while preserving supported SSML tags.

        Args:
            input_text (str): The input text containing TSS markup tags.

        Returns:
            str: Cleaned text with unsupported TSS markup tags removed.
        """
        # List of SSML tags supported by both OpenAI and ElevenLabs
        supported_tags = [
            'speak', 'speak', 'lang', 'p', 'phoneme',
            's', 'say-as', 'sub'
        ]
        # Append additional tags to the supported tags list
        # Create a pattern that matches any tag not in the supported list
        pattern = r'<(?!(?:/?' + '|'.join(supported_tags) + r')\b)[^>]+>'

        # Remove unsupported tags
        cleaned_text = re.sub(pattern, '', input_text)

        # Remove any leftover empty lines
        cleaned_text = re.sub(r'\n\s*\n', '\n', cleaned_text)
        cleaned_text = cleaned_text.replace('(scratchpad)', '')
        return cleaned_text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "speaker": self.speaker.name,
            "tts_args": self.tts_args
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], characters: Dict[str, Character]) -> 'TranscriptSegment':
        return cls(
            text=data['text'],
            speaker=characters[data['speaker']],
            tts_args=data.get('tts_args', {})
        )


class Transcript:
    def __init__(self, segments: List[TranscriptSegment], metadata: Dict[str, Any] = {}) -> None:
        self.segments = segments
        self.metadata = metadata

    def export(self, filepath: str, format_: str = "plaintext") -> None:
        """Export the transcript to a file."""
        with open(filepath, 'w') as f:
            if format_ == "plaintext":
                f.write(str(self))
            elif format_ == "json":
                json.dump(self.to_dict(), f, indent=2)
            else:
                raise ValueError(f"Unsupported format: {format_}")

    def dump(self, filepath: str) -> None:
        """Dump the transcript to a JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @staticmethod
    def _parse_legacy_transcript(content: str) -> List[Tuple[str, str]]:
        pattern = r'<Person(\d)>\s*(.*?)\s*</Person\1>'
        matches = re.findall(pattern, content, re.DOTALL)
        return [('Person' + person_num, text) for person_num, text in matches]

    @classmethod
    def load(cls, filepath: str, characters: Dict[str, Character]) -> 'Transcript':
        """Load a transcript from a JSON file."""
        # There are a loss of characters informations when loading a transcript, is it acceptable?
        with open(filepath, 'r') as f:
            content = f.read()

        try:
            data = json.loads(content)
            segments = [TranscriptSegment.from_dict(seg, characters) for seg in data['segments']]
        except json.JSONDecodeError:
            # If JSON parsing fails, assume it's a legacy transcript
            parsed_content = cls._parse_legacy_transcript(content)
            segments = []
            for speaker, text in parsed_content:
                if speaker in characters:
                    character = characters[speaker]
                else:
                    # Create a new character if it doesn't exist
                    character = Character(speaker, f"Character {speaker}", {})
                    characters[speaker] = character
                segments.append(TranscriptSegment(text, character))

        data = {'segments': segments, 'metadata': {}}
        return cls(segments, data['metadata'])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segments": [segment.to_dict() for segment in self.segments],
            "metadata": self.metadata
        }

    def __str__(self) -> str:
        """Convert the transcript to a string representation."""
        lines = []
        for segment in self.segments:
            lines.append(f"{segment.speaker.name}: {segment.text}")

        metadata_str = "\n".join([f"{key}: {value}" for key, value in self.metadata.items()])

        return f"Metadata:\n{metadata_str}\n\nTranscript:\n" + "\n".join(lines)
