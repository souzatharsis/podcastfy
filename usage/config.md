# Podcastfy Configuration

## API keys

The project uses a combination of a `.env` file for managing API keys and sensitive information, and a `config.yaml` file for non-sensitive configuration settings. Follow these steps to set up your configuration:

1. Create a `.env` file in the root directory of the project.
2. Add your API keys and other sensitive information to the `.env` file. For example:

   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here
   ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
   ```
API Key Requirements:
- OPENAI_API_KEY: Mandatory for all operations. (get your API key from [OpenAI](https://platform.openai.com/account/api-keys))
- ELEVENLABS_API_KEY: Required for audio generation (paid service). Edge TTS can be also used for audio generation without an API key.

Ensure you have the necessary API keys based on your intended usage of Podcastfy. Note: Never share your `.env` file or commit it to version control. It contains sensitive information that should be kept private. The `config.yaml` file can be shared and version-controlled as it doesn't contain sensitive data.

## Example Configurations

Here's a table showing example configurations:

| Configuration | Base LLM | TTS Model | API Keys Required |
|---------------|----------|-----------|-------------------|
| Default | Gemini | OpenAI | GEMINI_API_KEY and OPENAI_API_KEY |
| No API Keys Required | Local LLM | Edge | None |
| Optimal | Gemini | ElevenLabs | GEMINI_API_KEY and ELEVENLABS_API_KEY |


## Conversation Configuration

See [conversation_custom.md](conversation_custom.md) for more details.

## Running Local LLMs

See [local_llm.md](local_llm.md) for more details.

## Optional configuration

The `config.yaml` file in the root directory contains non-sensitive configuration settings. You can modify this file to adjust various parameters such as output directories, text-to-speech settings, and content generation options.

The application will automatically load the environment variables from `.env` and the configuration settings from `config.yaml` when it runs.

See [Configuration](config_custom.md) if you would like to further customize settings.
