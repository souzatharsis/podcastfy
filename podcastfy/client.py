"""
Podcastfy CLI

This module provides a command-line interface for generating podcasts or transcripts
from URLs or existing transcript files. It orchestrates the content extraction,
generation, and text-to-speech conversion processes.
"""
import copy

import os
import uuid
import typer
import yaml

from podcastfy.aiengines.llm.gemini_langchain import DefaultPodcastifyTranscriptEngine
from podcastfy.aiengines.tts.base import TTSBackend
from podcastfy.aiengines.tts.tts_backends import OpenAITTS, ElevenLabsTTS, EdgeTTS
from podcastfy.core.audio import AudioManager
from podcastfy.core.character import Character
from podcastfy.core.content import Content
from podcastfy.core.podcast import Podcast
from podcastfy.core.transcript import Transcript
from podcastfy.content_parser.content_extractor import ContentExtractor
from podcastfy.core.tts_configs import TTSConfig
from podcastfy.utils.config import Config, load_config
from podcastfy.utils.config_conversation import (
    load_conversation_config,
)
from podcastfy.utils.logger import setup_logger
from typing import List, Optional, Dict, Any

logger = setup_logger(__name__)

app = typer.Typer()

def create_characters(config: Dict[str, Any]) -> List[Character]:
    # in the future, we should load this from the config file
    host = Character(
        name="Person1",
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
        name="Person2",
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


def create_tts_backends(config: Config) -> List[TTSBackend]:
    return [
        OpenAITTS(api_key=config.OPENAI_API_KEY),
        ElevenLabsTTS(api_key=config.ELEVENLABS_API_KEY),
        EdgeTTS(),
    ]



def process_content(
        urls: Optional[List[str]] = None,
        transcript_file: Optional[str] = None,
        tts_model: str = "openai",  # to be fixed, in case of characters, it should be a list of models
        generate_audio: bool = True,
        config: Optional[Config] = None,
        conversation_config: Optional[Dict[str, Any]] = None,
        image_paths: Optional[List[str]] = None,
        is_local: bool = False,
) -> str:
    try:
        if config is None:
            config = load_config()
        if urls is None:
            urls = []
            if config is None:
                config = load_config()
        # Load default conversation config
        conv_config = load_conversation_config()

        # Update with provided config if any
        if conversation_config:
            conv_config.configure(conversation_config)
        characters = create_characters(conv_config.config_conversation)
        tts_backends = obtain_tts_backend(config, tts_model)
        audio_format = conv_config.config_conversation.get('text_to_speech')['audio_format']
        temp_dir = conv_config.config_conversation.get('text_to_speech').get('temp_audio_dir')
        audio_manager = AudioManager(tts_backends, audio_format=audio_format, audio_temp_dir=temp_dir, n_jobs=4)
        if transcript_file:
            logger.info(f"Using transcript file: {transcript_file}")
            transcript = Transcript.load(
                transcript_file, {char.name: char for char in characters}
            )
            podcast = Podcast.from_transcript(transcript, audio_manager, characters)
        else:
            logger.info(f"Processing {len(urls)} links")
            content_extractor = ContentExtractor()
            content_generator = DefaultPodcastifyTranscriptEngine(
                config.GEMINI_API_KEY, conversation_config, is_local=is_local
            )

            contents = [content_extractor.extract_content(url) for url in urls]
            llm_contents = []
            if contents:
                llm_contents.append(Content(value="\n\n".join(contents), type="text"))
            if image_paths:
                llm_contents.extend(
                    [Content(value=image_path, type="image_path") for image_path in image_paths]
                )
            podcast = Podcast(
                content=llm_contents,
                llm_backend=content_generator,
                audio_manager=audio_manager,
                characters=characters,
            )

        directories = config.get("output_directories")
        random_filename_no_suffix = f"podcast_{uuid.uuid4().hex}"
        random_filename_mp3 = f"{random_filename_no_suffix}.mp3"
        random_filename_transcript = f"{random_filename_no_suffix}.txt"
        if generate_audio:
            podcast.finalize()

            # for the sake of the tests currently in place, but in the future, we should remove this and return the podcast object
            audio_file = os.path.join(
                directories["audio"], random_filename_mp3
            )
            podcast.transcript.export(os.path.join(directories["transcripts"], random_filename_transcript))
            podcast.save(filepath=audio_file)
            return audio_file  # note: should return the podcast object instead, but for the sake of the tests, we return the audio file
        else:
            podcast.build_transcript()
            podcast.transcript.export(os.path.join(directories["transcripts"], random_filename_transcript))
            logger.info(f"Transcript generated successfully: {random_filename_transcript}")
            return random_filename_transcript
    except Exception as e:
        logger.error(f"An error occurred in the process_content function: {str(e)}")
        raise


def obtain_tts_backend(config, tts_model) -> Dict[str, TTSBackend]:
    # temporary solution
    tts_backends = create_tts_backends(config)
    # filter out the tts backends that are not in the tts_model, temporary solution
    tts_backends = {tts.name: tts for tts in tts_backends if tts.name == tts_model}
    return tts_backends


@app.command()
def main(
    urls: list[str] = typer.Option(None, "--url", "-u", help="URLs to process"),
    file: typer.FileText = typer.Option(
        None, "--file", "-f", help="File containing URLs, one per line"
    ),
    transcript: typer.FileText = typer.Option(
        None, "--transcript", "-t", help="Path to a transcript file"
    ),
    tts_model: str = typer.Option(
        None,
        "--tts-model",
        "-tts",
        help="TTS model to use (openai, elevenlabs or edge)",
    ),
    transcript_only: bool = typer.Option(
        False, "--transcript-only", help="Generate only a transcript without audio"
    ),
    conversation_config_path: str = typer.Option(
        None,
        "--conversation-config",
        "-cc",
        help="Path to custom conversation configuration YAML file",
    ),
    image_paths: List[str] = typer.Option(
        None, "--image", "-i", help="Paths to image files to process"
    ),
    is_local: bool = typer.Option(
        False,
        "--local",
        "-l",
        help="Use a local LLM instead of a remote one (http://localhost:8080)",
    ),
):
    """
    Generate a podcast or transcript from a list of URLs, a file containing URLs, a transcript file, or image files.
    """
    try:
        config = load_config()
        main_config = config.get("main", {})

        conversation_config = None
        # Load conversation config if provided
        if conversation_config_path:
            with open(conversation_config_path, "r") as f:
                conversation_config: Dict[str, Any] | None = yaml.safe_load(f)
            
                
                
        # Use default TTS model from conversation config if not specified
        if tts_model is None:
            tts_config = load_conversation_config().get('text_to_speech', {})
            tts_model = tts_config.get('default_tts_model', 'openai')
            
        if transcript:
            if image_paths:
                logger.warning("Image paths are ignored when using a transcript file.")
            final_output = process_content(
                transcript_file=transcript.name,
                tts_model=tts_model,
                generate_audio=not transcript_only,
                conversation_config=conversation_config,
                config=config,
                is_local=is_local,
            )
        else:
            urls_list = urls or []
            if file:
                urls_list.extend([line.strip() for line in file if line.strip()])

            if not urls_list and not image_paths:
                raise typer.BadParameter(
                    "No input provided. Use --url to specify URLs, --file to specify a file containing URLs, --transcript for a transcript file, or --image for image files."
                )

            final_output = process_content(
                urls=urls_list,
                tts_model=tts_model,
                generate_audio=not transcript_only,
                config=config,
                conversation_config=conversation_config,
                image_paths=image_paths,
                is_local=is_local,
            )

        if transcript_only:
            typer.echo(f"Transcript generated successfully: {final_output}")
        else:
            typer.echo(
                f"Podcast generated successfully using {tts_model} TTS model: {final_output}"
            )

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
    image_paths: Optional[List[str]] = None,
    is_local: bool = False,
) -> Optional[str]:
    """
    Generate a podcast or transcript from a list of URLs, a file containing URLs, a transcript file, or image files.

    Args:
        urls (Optional[List[str]]): List of URLs to process.
        url_file (Optional[str]): Path to a file containing URLs, one per line.
        transcript_file (Optional[str]): Path to a transcript file.
        tts_model (Optional[str]): TTS model to use ('openai', 'elevenlabs' or 'edge').
        transcript_only (bool): Generate only a transcript without audio. Defaults to False.
        config (Optional[Dict[str, Any]]): User-provided configuration dictionary.
        conversation_config (Optional[Dict[str, Any]]): User-provided conversation configuration dictionary.
        image_paths (Optional[List[str]]): List of image file paths to process.
        is_local (bool): Whether to use a local LLM. Defaults to False.

    Returns:
        Optional[str]: Path to the final podcast audio file, or None if only generating a transcript.

    Example:
        >>> from podcastfy.client import generate_podcast
        >>> result = generate_podcast(
        ...     image_paths=['/path/to/image1.jpg', '/path/to/image2.png'],
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
        ...     },
        ...     is_local=True
        ... )
    """
    try:
        # Load default config
        default_config = load_config()

        # Update config if provided
        if config:
            if isinstance(config, dict):
                # Create a deep copy of the default config
                updated_config = copy.deepcopy(default_config)
                # Update the copy with user-provided values
                updated_config.configure(**config)
                default_config = updated_config
            elif isinstance(config, Config):
                # If it's already a Config object, use it directly
                default_config = config
            else:
                raise ValueError(
                    "Config must be either a dictionary or a Config object"
                )

        main_config = default_config.config.get("main", {})

        # Use provided tts_model if specified, otherwise use the one from config
        if tts_model is None:
            tts_model = main_config.get("default_tts_model", "openai")

        if transcript_file:
            if image_paths:
                logger.warning("Image paths are ignored when using a transcript file.")
            return process_content(
                transcript_file=transcript_file,
                tts_model=tts_model,
                generate_audio=not transcript_only,
                config=default_config,
                conversation_config=conversation_config,
                is_local=is_local,
            )
        else:
            urls_list = urls or []
            if url_file:
                with open(url_file, "r") as file:
                    urls_list.extend([line.strip() for line in file if line.strip()])

            if not urls_list and not image_paths:
                raise ValueError(
                    "No input provided. Please provide either 'urls', 'url_file', 'transcript_file', or 'image_paths'."
                )

            return process_content(
                urls=urls_list,
                tts_model=tts_model,
                generate_audio=not transcript_only,
                config=default_config,
                conversation_config=conversation_config,
                image_paths=image_paths,
                is_local=is_local,
            )

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise
