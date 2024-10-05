# Podcastfy Configuration

The project uses a combination of a `.env` file for managing API keys and sensitive information, and a `config.yaml` file for non-sensitive configuration settings. Follow these steps to set up your configuration:

1. Create a `.env` file in the root directory of the project.
2. Add your API keys and other sensitive information to the `.env` file. For example:

   ```
   JINA_API_KEY=your_jina_api_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here
   ```
API Key Requirements:
- JINA_API_KEY: Required only for parsing website content as input. (free tier available)
- GEMINI_API_KEY: Mandatory for all operations. (free tier available)
- OPENAI_API_KEY or ELEVENLABS_API_KEY: At least one is required for audio generation. (paid service)

Ensure you have the necessary API keys based on your intended usage of Podcastfy.

3. The `config.yaml` file in the root directory contains non-sensitive configuration settings. You can modify this file to adjust various parameters such as output directories, text-to-speech settings, and content generation options.

The application will automatically load the environment variables from `.env` and the configuration settings from `config.yaml` when it runs.

Note: Never share your `.env` file or commit it to version control. It contains sensitive information that should be kept private. The `config.yaml` file can be shared and version-controlled as it doesn't contain sensitive data.

See [Configuration](config_custom.md) if you would like to further customize settings.
