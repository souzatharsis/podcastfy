# Podcastfy Advanced Configuration Guide

Podcastfy uses a `config.yaml` file to manage various settings and parameters. This guide explains each configuration option available in the file.

## Output Directories

- `transcripts`: "./data/transcripts"
  - Directory where generated transcripts are saved.
- `audio`: "./data/audio"
  - Directory where generated audio files are saved.

## Text-to-Speech (TTS) Settings

### ElevenLabs TTS

- `default_voices`:
  - `question`: "Chris"
    - Default voice for questions in the podcast.
  - `answer`: "BrittneyHart"
    - Default voice for answers in the podcast.
- `model`: "eleven_multilingual_v2"
  - The ElevenLabs TTS model to use.

### OpenAI TTS

- `default_voices`:
  - `question`: "echo"
    - Default voice for questions using OpenAI TTS.
  - `answer`: "shimmer"
    - Default voice for answers using OpenAI TTS.
- `model`: "tts-1-hd"
  - The OpenAI TTS model to use.

### General TTS Settings

- `audio_format`: "mp3"
  - Format of the generated audio files.
- `temp_audio_dir`: "data/audio/tmp/"
  - Temporary directory for audio processing.
- `ending_message`: "Tchau!"
  - Message to be appended at the end of the podcast.

## Content Generator

- `gemini_model`: "gemini-1.5-pro-latest"
  - The Gemini AI model used for content generation.
- `system_prompt_file`: "prompt.txt"
  - File containing the system prompt for content generation.

## Content Extractor

- `youtube_url_patterns`:
  - Patterns to identify YouTube URLs.
  - Current patterns: "youtube.com", "youtu.be"

## Website Extractor

- `jina_api_url`: "https://r.jina.ai"
  - URL for the Jina API used in content extraction.
- `markdown_cleaning`:
  - `remove_patterns`:
    - Patterns to remove from extracted markdown content.
    - Current patterns remove image links, hyperlinks, and URLs.

## YouTube Transcriber

- `remove_phrases`:
  - Phrases to remove from YouTube transcriptions.
  - Current phrase: "[music]"

## Logging

- `level`: "INFO"
  - Default logging level.
- `format`: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  - Format string for log messages.

## Main Settings

- `default_tts_model`: "openai"
  - Default Text-to-Speech model to use when not specified.

To customize Podcastfy, modify these settings in the `config.yaml` file according to your preferences and requirements.
