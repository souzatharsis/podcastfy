"""
Podcastfy CLI

This module provides a command-line interface for generating podcasts or transcripts
from URLs or existing transcript files. It orchestrates the content extraction,
generation, and text-to-speech conversion processes.
"""

import os
import uuid
import typer
import yaml
from podcastfy.content_parser.content_extractor import ContentExtractor
from podcastfy.content_generator import ContentGenerator
from podcastfy.text_to_speech import TextToSpeech
from podcastfy.utils.config import Config, load_config
from podcastfy.utils.config_conversation import (
    ConversationConfig,
    load_conversation_config,
)
from podcastfy.utils.logger import setup_logger
from typing import List, Optional, Dict, Any
import copy


logger = setup_logger(__name__)

app = typer.Typer()

os.environ["LANGCHAIN_TRACING_V2"] = "false"


def process_content(
    urls=None,
    transcript_file=None,
    tts_model="openai",
    generate_audio=True,
    config=None,
    conversation_config: Optional[Dict[str, Any]] = None,
    image_paths: Optional[List[str]] = None,
    is_local: bool = False,
    text: Optional[str] = None,
):
    """
    Process URLs, a transcript file, image paths, or raw text to generate a podcast or transcript.

    Args:
        urls (Optional[List[str]]): A list of URLs to process.
        transcript_file (Optional[str]): Path to a transcript file.
        tts_model (str): The TTS model to use ('openai', 'elevenlabs' or 'edge'). Defaults to 'openai'.
        generate_audio (bool): Whether to generate audio or just a transcript. Defaults to True.
        config (Config): Configuration object to use. If None, default config will be loaded.
        conversation_config (Optional[Dict[str, Any]]): Custom conversation configuration.
        image_paths (Optional[List[str]]): List of image file paths to process.
        is_local (bool): Whether to use a local LLM. Defaults to False.
        text (Optional[str]): Raw text input to be processed.

    Returns:
        Optional[str]: Path to the final podcast audio file, or None if only generating a transcript.
    """
    try:
        if config is None:
            config = load_config()
        
        # Load default conversation config
        conv_config = load_conversation_config()
        
        # Update with provided config if any
        if conversation_config:
            conv_config.configure(conversation_config)

        if transcript_file:
            logger.info(f"Using transcript file: {transcript_file}")
            with open(transcript_file, "r") as file:
                qa_content = file.read()
        else:
            content_generator = ContentGenerator(
                api_key=config.GEMINI_API_KEY, conversation_config=conv_config.to_dict()
            )

            combined_content = ""

            if urls:
                logger.info(f"Processing {len(urls)} links")
                content_extractor = ContentExtractor()
                # Extract content from links
                contents = [content_extractor.extract_content(link) for link in urls]
                # Combine all extracted content
                combined_content += "\n\n".join(contents)

            if text:
                combined_content += f"\n\n{text}"

            # Generate Q&A content
            random_filename = f"transcript_{uuid.uuid4().hex}.txt"
            transcript_filepath = os.path.join(
                config.get("output_directories")["transcripts"], random_filename
            )
            qa_content = content_generator.generate_qa_content(
                combined_content,
                image_file_paths=image_paths or [],
                output_filepath=transcript_filepath,
                is_local=is_local,
            )

        if generate_audio:
            api_key = None
            # edge does not require an API key
            if tts_model != "edge":
                api_key = getattr(config, f"{tts_model.upper()}_API_KEY")

            text_to_speech = TextToSpeech(model=tts_model, api_key=api_key, conversation_config=conv_config.to_dict())
            # Convert text to speech using the specified model
            random_filename = f"podcast_{uuid.uuid4().hex}.mp3"
            audio_file = os.path.join(
                config.get("output_directories")["audio"], random_filename
            )
            text_to_speech.convert_to_speech(qa_content, audio_file)
            logger.info(f"Podcast generated successfully using {tts_model} TTS model")
            return audio_file
        else:
            logger.info(f"Transcript generated successfully: {transcript_filepath}")
            return transcript_filepath

    except Exception as e:
        logger.error(f"An error occurred in the process_content function: {str(e)}")
        raise


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
    text: str = typer.Option(
        None, "--text", "-txt", help="Raw text input to be processed"
    ),
):
    """
    Generate a podcast or transcript from a list of URLs, a file containing URLs, a transcript file, image files, or raw text.
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
                text=text,
            )
        else:
            urls_list = urls or []
            if file:
                urls_list.extend([line.strip() for line in file if line.strip()])

            if not urls_list and not image_paths and not text:
                raise typer.BadParameter(
                    "No input provided. Use --url to specify URLs, --file to specify a file containing URLs, --transcript for a transcript file, --image for image files, or --text for raw text input."
                )

            final_output = process_content(
                urls=urls_list,
                tts_model=tts_model,
                generate_audio=not transcript_only,
                config=config,
                conversation_config=conversation_config,
                image_paths=image_paths,
                is_local=is_local,
                text=text,
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
    text: Optional[str] = None,  # Add the text parameter here
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
        text (Optional[str]): Raw text input to be processed.

    Returns:
        Optional[str]: Path to the final podcast audio file, or None if only generating a transcript.
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
                text=text,  # Pass the text parameter here
            )
        else:
            urls_list = urls or []
            if url_file:
                with open(url_file, "r") as file:
                    urls_list.extend([line.strip() for line in file if line.strip()])

            if not urls_list and not image_paths and not text:
                raise ValueError(
                    "No input provided. Please provide either 'urls', 'url_file', 'transcript_file', 'image_paths', or 'text'."
                )

            return process_content(
                urls=urls_list,
                tts_model=tts_model,
                generate_audio=not transcript_only,
                config=default_config,
                conversation_config=conversation_config,
                image_paths=image_paths,
                is_local=is_local,
                text=text
            )

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise
