# Podcastfy

Podcastfy: Your GenAI-Powered Companion for Transforming Text into Captivating Audio Conversations

Podcastfy is an LLM-based Python package and CLI tool that enables programatic creation of engaging audio podcasts from web content and text sources. Unlike tools focused primarily on note-taking or research synthesis (e.g. NotebookLM ❤️), Podcastfy specializes and focuses solely on the programatic generation of engaging, conversational audio from a multitude of text sources.

Ideal for Developers that build data-driven products for creators, educators, and researchers seeking to transform written information into easily digestible audio content. Podcastfy offers a unique solution for bridging the gap between text and audio consumption, programatically.

## Features

- Extract and synthesize content from multiple web sources (URLs and PDFs)
- Generate engaging, AI-powered conversational content from extracted text
- Create high-quality transcripts from diverse textual information sources
- Convert pre-existing transcript files into dynamic podcast episodes
- Support for multiple advanced text-to-speech models (OpenAI and ElevenLabs) for natural-sounding audio
- Support for multiple languages, enabling global content creation
- Seamlessly integrate CLI with content management systems for streamlined workflows


## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/podcastfy.git
   cd podcastfy
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

Podcastfy can be used as a command-line interface (CLI) tool. Here are some usage examples:

1. Generate a podcast from URLs using OpenAI TTS (default):
   ```
   python -m podcastfy.main --url https://example.com/article1 --url https://example.com/article2
   ```

2. Generate a podcast from URLs using ElevenLabs TTS:
   ```
   python -m podcastfy.main --url https://example.com/article1 --url https://example.com/article2 --tts-model elevenlabs
   ```

3. Generate a podcast from a file containing URLs:
   ```
   python -m podcastfy.main --file path/to/urls.txt
   ```

4. Generate a podcast from an existing transcript file:
   ```
   python -m podcastfy.main --transcript path/to/transcript.txt
   ```

5. Generate only a transcript (without audio) from URLs:
   ```
   python -m podcastfy.main --url https://example.com/article1 --transcript-only
   ```

6. Generate a podcast using a combination of URLs and a file:
   ```
   python -m podcastfy.main --url https://example.com/article1 --file path/to/urls.txt --tts-model openai
   ```

For more information on available options, use:
   ```
   python -m podcastfy.main --help
   ```
    

## Configuration

The project uses a `.env` file for managing API keys and other sensitive information. Follow these steps to set up your configuration:

1. Create a `.env` file in the root directory of the project.
2. Add your API keys and other configuration variables to the `.env` file. For example:

   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
   JINA_API_KEY=your_jina_api_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

The application will automatically load these environment variables when it runs.

Note: Never share your `.env` file or commit it to version control. It contains sensitive information that should be kept private.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-nc-sa/4.0/).

## Disclaimer

This tool is designed for personal or educational use. Please ensure you have the necessary rights or permissions before using content from external sources for podcast creation. All audio content is AI-generated and it is not intended to clone real-life humans!