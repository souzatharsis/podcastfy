import os
import uuid
import typer
from pathlib import Path
from typing import List, Optional, Dict, Any, Union, Tuple

from podcastfy.aiengines.llm.gemini_langchain import DefaultPodcastifyTranscriptEngine
from podcastfy.aiengines.tts.tts_backends import OpenAITTS, ElevenLabsTTS, EdgeTTS
from podcastfy.core.character import Character
from podcastfy.core.llm_content import LLMContent
from podcastfy.core.podcast import Podcast, SyncTTSBackend, AsyncTTSBackend
from podcastfy.core.transcript import Transcript
from podcastfy.content_parser.content_extractor import ContentExtractor
from podcastfy.core.tts_configs import TTSConfig
from podcastfy.utils.config import Config, load_config
from podcastfy.utils.config_conversation import load_conversation_config
from podcastfy.utils.logger import setup_logger

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


def create_tts_backends(config: Config) -> List[Union[SyncTTSBackend, AsyncTTSBackend]]:
    return [
        OpenAITTS(api_key=config.OPENAI_API_KEY),
        ElevenLabsTTS(api_key=config.ELEVENLABS_API_KEY),
        EdgeTTS(),
    ]



def process_content_v2(
    urls: Optional[List[str]] = None,
    transcript_file: Optional[str] = None,
    tts_model: str = "openai",  # to be fixed, in case of characters, it should be a list of models
    generate_audio: bool = True,
    config: Optional[Config] = None,
    conversation_config: Optional[Dict[str, Any]] = None,
    image_paths: Optional[List[str]] = None,
    is_local: bool = False,
) -> Tuple[Optional[str], Podcast]:
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
        tts_backends = create_tts_backends(config)
        # filter out the tts backends that are not in the tts_model, temporary solution
        tts_backends = [tts for tts in tts_backends if tts.name != tts_model]
        if transcript_file:
            logger.info(f"Using transcript file: {transcript_file}")
            transcript = Transcript.load(
                transcript_file, {char.name: char for char in characters}
            )
            podcast = Podcast.from_transcript(transcript, tts_backends, characters)
        else:
            logger.info(f"Processing {len(urls)} links")
            content_extractor = ContentExtractor()
            content_generator = DefaultPodcastifyTranscriptEngine(
                config.GEMINI_API_KEY, conversation_config, is_local=is_local
            )

            contents = [content_extractor.extract_content(url) for url in urls]
            llm_contents = []
            if contents:
                llm_contents.append(LLMContent(value="\n\n".join(contents), type="text"))
            if image_paths:
                llm_contents.extend(
                    [LLMContent(value=image_path, type="image_path") for image_path in image_paths]
                )



            podcast = Podcast(
                content=llm_contents,
                llm_backend=content_generator,
                tts_backends=tts_backends,
                characters=characters,
            )


        if generate_audio:
            podcast.finalize()

            # for the sake of the tests currently in place, but in the future, we should remove this and return the podcast object
            random_filename = f"podcast_{uuid.uuid4().hex}.mp3"
            audio_file = os.path.join(
                config.get("output_directories")["audio"], random_filename
            )
            podcast.save(filepath=audio_file)
            return audio_file
        else:
            podcast.build_transcript()

        return podcast
    except Exception as e:
        logger.error(f"An error occurred in the process_content function: {str(e)}")
        raise
