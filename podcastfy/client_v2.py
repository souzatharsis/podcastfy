import os
import uuid
import typer
from pathlib import Path
from typing import List, Optional, Dict, Any, Union

from podcastfy.aiengines.llm.gemini_langchain import DefaultPodcastifyTranscriptEngine
from podcastfy.aiengines.tts.tts_backends import OpenAITTS, ElevenLabsTTS, EdgeTTS
from podcastfy.core.character import Character
from podcastfy.core.podcast import Podcast, SyncTTSBackend, AsyncTTSBackend
from podcastfy.core.transcript import Transcript
from podcastfy.content_parser.content_extractor import ContentExtractor
from podcastfy.core.tts_configs import TTSConfig
from podcastfy.utils.config import Config, load_config
from podcastfy.utils.logger import setup_logger

logger = setup_logger(__name__)

app = typer.Typer()


def create_characters(config: Dict[str, Any]) -> List[Character]:
    host = Character(
        name="Host",
        role="Podcast host",
        tts_configs={
            "openai": TTSConfig(
                voice=config["text_to_speech"]["openai"]["default_voices"]["question"],
                backend="openai",
            ),
            "elevenlabs": TTSConfig(
                voice=config["text_to_speech"]["elevenlabs"]["default_voices"][
                    "question"
                ],
                backend="elevenlabs",
            ),
        },
        default_description_for_llm="{name} is an enthusiastic podcast host. Speaks clearly and engagingly.",
    )

    guest = Character(
        name="Guest",
        role="Expert guest",
        tts_configs={
            "openai": TTSConfig(
                voice=config["text_to_speech"]["openai"]["default_voices"]["answer"],
                backend="openai",
            ),
            "elevenlabs": TTSConfig(
                voice=config["text_to_speech"]["elevenlabs"]["default_voices"][
                    "answer"
                ],
                backend="elevenlabs",
            ),
        },
        default_description_for_llm="{name} is an expert guest. Shares knowledge in a friendly manner.",
    )

    return [host, guest]


def create_tts_backends(config: Config) -> List[Union[SyncTTSBackend, AsyncTTSBackend]]:
    return [
        OpenAITTS(api_key=config.OPENAI_API_KEY),
        ElevenLabsTTS(api_key=config.ELEVENLABS_API_KEY),
        EdgeTTS(),
    ]


def process_links(
    links: List[str],
    transcript_file: Optional[str] = None,
    tts_model: str = "openai",  # could be removed now ?
    generate_audio: bool = True,
    config: Optional[Config] = None,
    conversation_config: Optional[Dict[str, Any]] = None,
) -> Podcast:
    if config is None:
        config = load_config()
    characters = create_characters(config.config)
    tts_backends = create_tts_backends(config)
    if transcript_file:
        logger.info(f"Using transcript file: {transcript_file}")
        transcript = Transcript.load(
            transcript_file, {char.name: char for char in characters}
        )
        podcast = Podcast.from_transcript(transcript, tts_backends, characters)
    else:
        logger.info(f"Processing {len(links)} links")
        content_extractor = ContentExtractor(config.JINA_API_KEY)
        content_generator = DefaultPodcastifyTranscriptEngine(
            config.GEMINI_API_KEY, conversation_config
        )

        contents = [content_extractor.extract_content(link) for link in links]
        combined_content = "\n\n".join(contents)

        llm_backend = content_generator  # Assuming ContentGenerator implements the LLMBackend interface

        podcast = Podcast(
            content=combined_content,
            llm_backend=llm_backend,
            tts_backends=tts_backends,
            characters=characters,
        )

    if generate_audio:
        podcast.finalize()
    else:
        podcast.build_transcript()

    return podcast


@app.command()
def main(
    urls: List[str] = typer.Option(None, "--url", "-u", help="URLs to process"),
    file: typer.FileText = typer.Option(
        None, "--file", "-f", help="File containing URLs, one per line"
    ),
    transcript: typer.FileText = typer.Option(
        None, "--transcript", "-t", help="Path to a transcript file"
    ),
    tts_model: str = typer.Option(
        None, "--tts-model", "-tts", help="TTS model to use (openai or elevenlabs)"
    ),
    transcript_only: bool = typer.Option(
        False, "--transcript-only", help="Generate only a transcript without audio"
    ),
    conversation_config: str = typer.Option(
        None,
        "--conversation-config",
        "-cc",
        help="Path to custom conversation configuration YAML file",
    ),
    output_dir: str = typer.Option(
        "./output", "--output-dir", "-o", help="Directory to save output files"
    ),
):
    """
    Generate a podcast or transcript from a list of URLs, a file containing URLs, or a transcript file.
    """
    try:
        config = load_config()
        main_config = config.config.get("main", {})
        if tts_model is None:
            tts_model = main_config.get("default_tts_model", "openai")

        urls_list = urls or []
        if file:
            urls_list.extend([line.strip() for line in file if line.strip()])

        if not urls_list and not transcript:
            raise typer.BadParameter(
                "No URLs or transcript provided. Use --url to specify URLs, --file to specify a file containing URLs, or --transcript for a transcript file."
            )

        podcast = process_links(
            urls_list,
            transcript_file=transcript.name if transcript else None,
            tts_model=tts_model,
            generate_audio=not transcript_only,
            config=config,
            conversation_config=conversation_config,
        )

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if transcript_only:
            transcript_file = output_dir / f"transcript_{uuid.uuid4().hex}.txt"
            podcast.export_transcript(str(transcript_file))
            typer.echo(f"Transcript generated successfully: {transcript_file}")
        else:
            audio_file = output_dir / f"podcast_{uuid.uuid4().hex}.mp3"
            podcast.save(str(audio_file))
            transcript_file = output_dir / f"transcript_{uuid.uuid4().hex}.txt"
            podcast.export_transcript(str(transcript_file))
            typer.echo(
                f"Podcast generated successfully using {tts_model} TTS model: {audio_file}"
            )
            typer.echo(f"Transcript saved to: {transcript_file}")

    except Exception as e:
        typer.echo(f"An error occurred: {str(e)}", err=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()


def generate_podcast(
    urls: Optional[List[str]] = None,
    url_file: Optional[str] = None,
    transcript_file: Optional[str] = None,
    tts_model: Optional[str] = None,
    transcript_only: bool = False,
    config: Optional[Dict[str, Any]] = None,
    conversation_config: Optional[Dict[str, Any]] = None,
) -> Podcast:
    """
    Generate a podcast or transcript from a list of URLs, a file containing URLs, or a transcript file.

    Args:
        urls (Optional[List[str]]): List of URLs to process.
        url_file (Optional[str]): Path to a file containing URLs, one per line.
        transcript_file (Optional[str]): Path to a transcript file.
        tts_model (Optional[str]): TTS model to use ('openai' or 'elevenlabs').
        transcript_only (bool): Generate only a transcript without audio. Defaults to False.
        config (Optional[Dict[str, Any]]): User-provided configuration dictionary.
        conversation_config (Optional[Dict[str, Any]]): User-provided conversation configuration dictionary.

    Returns:
        Podcast: An instance of the Podcast class representing the generated podcast.

    Example:
        >>> from podcastfy.client_v2 import generate_podcast
        >>> podcast = generate_podcast(
        ...     urls=['https://example.com/article1', 'https://example.com/article2'],
        ...     tts_model='elevenlabs',
        ...     config={
        ...         'main': {
        ...             'default_tts_model': 'elevenlabs'
        ...         },
        ...         'output_directories': {
        ...             'audio': '/custom/path/to/audio',
        ...             'transcripts': '/custom/path/to/transcripts'
        ...         }
        ...     },
        ...     conversation_config={
        ...         'word_count': 150,
        ...         'conversation_style': ['informal', 'friendly'],
        ...         'podcast_name': 'My Custom Podcast'
        ...     }
        ... )
        >>> podcast.save('/path/to/output.mp3')
        >>> podcast.export_transcript('/path/to/transcript.txt')
    """
    try:
        default_config = load_config()

        if config:
            if isinstance(config, dict):
                updated_config = Config()
                updated_config.configure(**config)
                default_config = updated_config
            elif isinstance(config, Config):
                default_config = config
            else:
                raise ValueError(
                    "Config must be either a dictionary or a Config object"
                )

        main_config = default_config.config.get("main", {})

        if tts_model is None:
            tts_model = main_config.get("default_tts_model", "openai")

        urls_list = urls or []
        if url_file:
            with open(url_file, "r") as file:
                urls_list.extend([line.strip() for line in file if line.strip()])

        if not urls_list and not transcript_file:
            raise ValueError(
                "No URLs or transcript provided. Please provide either 'urls', 'url_file', or 'transcript_file'."
            )

        podcast = process_links(
            urls_list,
            transcript_file=transcript_file,
            tts_model=tts_model,
            generate_audio=not transcript_only,
            config=default_config,
            conversation_config=conversation_config,
        )

        return podcast

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise
