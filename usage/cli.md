## CLI

Podcastfy can be used as a command-line interface (CLI) tool. See below some usage examples.
Please make sure you follow configuration instructions first - [See Setup](README.md#setup).

1. Generate a podcast from URLs using OpenAI TTS (default):
   ```
   python -m podcastfy.client --url https://example.com/article1 --url https://example.com/article2
   ```

2. Generate a podcast from URLs using ElevenLabs TTS:
   ```
   python -m podcastfy.client --url https://example.com/article1 --url https://example.com/article2 --tts-model elevenlabs
   ```

3. Generate a podcast from a file containing URLs:
   ```
   python -m podcastfy.client --file path/to/urls.txt
   ```

4. Generate a podcast from an existing transcript file:
   ```
   python -m podcastfy.client --transcript path/to/transcript.txt
   ```

5. Generate only a transcript (without audio) from URLs:
   ```
   python -m podcastfy.client --url https://example.com/article1 --transcript-only
   ```

6. Generate a podcast using a combination of URLs and a file:
   ```
   python -m podcastfy.client --url https://example.com/article1 --file path/to/urls.txt
   ```

7. Generate a podcast from image files:
   ```
   python -m podcastfy.client --image path/to/image1.jpg --image path/to/image2.png
   ```

8. Generate a podcast with a custom conversation configuration:
   ```
   python -m podcastfy.client --url https://example.com/article1 --conversation-config path/to/custom_config.yaml
   ```

9. Generate a podcast from URLs and images:
   ```
   python -m podcastfy.client --url https://example.com/article1 --image path/to/image1.jpg
   ```

10. Generate a transcript using a local LLM:
   ```
   python -m podcastfy.client --url https://example.com/article1 --transcript-only --local
   ```

11. Generate a podcast from a Markdown file:
   ```
   python -m podcastfy.client --url path/to/your/file.md
   ```

12. Generate a podcast from multiple Markdown files:
   ```
   python -m podcastfy.client --url path/to/file1.md --url path/to/file2.md
   ```

13. Generate a podcast from a mix of URLs and Markdown files:
   ```
   python -m podcastfy.client --url https://example.com/article1 --url path/to/file.md
   ```

For more information on available options, use:
   ```
   python -m podcastfy.client --help
   ```
