import os
import uuid
import typer
from pathlib import Path
from typing import List, Optional, Dict, Any, Union, Tuple

from podcastfy.aiengines.llm.gemini_langchain import DefaultPodcastifyTranscriptEngine
from podcastfy.aiengines.tts.base import TTSBackend
from podcastfy.aiengines.tts.tts_backends import OpenAITTS, ElevenLabsTTS, EdgeTTS
from podcastfy.core.audio import AudioManager
from podcastfy.core.character import Character
from podcastfy.core.content import Content
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


def create_tts_backends(config: Config) -> List[TTSBackend]:
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

        return None # note: should return the podcast object instead, but for the sake of the tests, we return None
    except Exception as e:
        logger.error(f"An error occurred in the process_content function: {str(e)}")
        raise


def obtain_tts_backend(config, tts_model) -> Dict[str, TTSBackend]:
    # temporary solution
    tts_backends = create_tts_backends(config)
    # filter out the tts backends that are not in the tts_model, temporary solution
    tts_backends = {tts.name: tts for tts in tts_backends if tts.name == tts_model}
    return tts_backends
