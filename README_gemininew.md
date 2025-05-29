# GeminiNewTTS Provider

The `GeminiNewTTS` provider is a new TTS provider for Podcastfy that uses Google's latest Gemini API with native text-to-speech capabilities. This provider supports both single-speaker and multi-speaker audio generation using the new `google-genai` SDK.

## Features

- **Multi-speaker support**: Generate conversations between two speakers with different voices
- **Single-speaker support**: Generate single-speaker audio for simple text
- **Advanced chunking**: Intelligent text chunking to handle long content while preserving speaker tags
- **High-quality audio**: Uses Google's latest Gemini 2.5 TTS models
- **MP3 output**: Generates high-quality MP3 audio files (compatible with existing system)
- **Auto-merging**: Automatically merges multiple audio chunks into a single file

## Installation

The provider requires the new `google-genai` package:

```bash
pip install google-genai==1.16.1
```

**Note**: This package requires specific versions of several dependencies. All dependency conflicts have been resolved in the requirements.txt file:

- `google-genai==1.16.1`
- `anyio==4.8.0` (updated from 4.6.2.post1 to satisfy google-genai requirements)
- `httpx==0.28.1` (updated from 0.27.2 to satisfy google-genai requirements)
- `google-resumable-media==2.7.2` (fixed typo from 2.72.0)

## Configuration

Add the following to your `conversation_config.yaml`:

```yaml
text_to_speech:
  gemininew:
    default_voices:
      question: "Kore" # Voice for first speaker
      answer: "Puck" # Voice for second speaker
    model: "gemini-2.5-flash-preview-tts"
```

## Available Voices

The provider supports 30 different voice options:

- **Zephyr** - Bright
- **Kore** - Firm
- **Orus** - Firm
- **Autonoe** - Bright
- **Umbriel** - Easy-going
- **Erinome** - Clear
- **Laomedeia** - Upbeat
- **Schedar** - Even
- **Achird** - Friendly
- **Sadachbia** - Lively
- **Puck** - Upbeat
- **Fenrir** - Excitable
- **Aoede** - Breezy
- **Enceladus** - Breathy
- **Algieba** - Smooth
- **Algenib** - Gravelly
- **Achernar** - Soft
- **Gacrux** - Mature
- **Zubenelgenubi** - Casual
- **Sadaltager** - Knowledgeable
- **Charon** - Informative
- **Leda** - Youthful
- **Callirrhoe** - Easy-going
- **Iapetus** - Clear
- **Despina** - Smooth
- **Rasalgethi** - Informative
- **Alnilam** - Firm
- **Pulcherrima** - Forward
- **Vindemiatrix** - Gentle
- **Sulafat** - Warm

## Usage

### Using via CLI

```bash
python -m podcastfy.cli --tts-model gemininew --url "https://example.com/article"
```

### Using via Python API

```python
from podcastfy import generate_podcast

# Generate a podcast using the new Gemini TTS
audio_file = generate_podcast(
    urls=["https://example.com/article"],
    tts_model="gemininew",
    api_key_label="GEMINI_API_KEY"  # Set your API key in environment
)
```

### Using with Custom Voices

```python
from podcastfy.tts.factory import TTSProviderFactory

# Create the provider with custom settings
provider = TTSProviderFactory.create(
    'gemininew',
    api_key="your-gemini-api-key",
    model="gemini-2.5-flash-preview-tts"
)

# Generate audio with custom voices
text = "<Person1>Hello, welcome to our podcast!</Person1><Person2>Thanks for having me!</Person2>"
audio_chunks = provider.generate_audio(
    text=text,
    voice="Zephyr",    # First speaker voice
    voice2="Sulafat",  # Second speaker voice
    model="gemini-2.5-flash-preview-tts"
)
```

## API Key Setup

You need a Google AI API key to use this provider:

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create a new API key
3. Set it as an environment variable:
   ```bash
   export GEMINI_API_KEY="your-api-key-here"
   ```

## Technical Details

### Context Limits

- Maximum context window: 32k tokens
- Default chunking size: 30,000 characters
- Automatic chunking preserves speaker tags and conversation flow

### Audio Format

- Output format: MP3 (compatible with existing system)
- Sample rate: 24,000 Hz (internally converted from Gemini's PCM output)
- Channels: 1 (mono)
- Bitrate: 320kbps
- Codec: libmp3lame

### Multi-Speaker Features

- Supports up to 2 speakers
- Automatic conversion from `<Person1>` and `<Person2>` tags to named speakers
- Intelligent merging of audio chunks
- Preserves conversation flow across chunks

### Error Handling

- Graceful fallback when chunks fail to merge
- Comprehensive logging for debugging
- Input validation for parameters

### Dependencies

- **google-genai**: New Google AI SDK for latest Gemini models
- **anyio**: Updated to 4.8.0 to satisfy google-genai requirements
- **pydub**: For audio processing and MP3 conversion
- **wave**: For PCM to WAV conversion (internal use)

## Differences from Other Providers

### vs. GeminiMultiTTS

- Uses new `google-genai` SDK instead of `google-cloud-texttospeech`
- Different API and authentication method
- Supports newer Gemini 2.5 models
- Different voice naming convention
- Both output MP3 format for compatibility

### vs. OpenAI TTS

- Better multi-speaker support with distinct voice characteristics
- More voice options (30 vs 6)
- Different chunking strategy optimized for conversations
- Uses Google's models instead of OpenAI's
- Both output MP3 format

## Troubleshooting

### Common Issues

1. **Import Error**: Make sure `google-genai` is installed

   ```bash
   pip install google-genai==1.16.1
   ```

2. **Dependency Conflict with anyio**: Ensure you have the correct `anyio` version

   ```bash
   pip install anyio==4.8.0
   ```

3. **Dependency Conflict with httpx**: Ensure you have the correct `httpx` version

   ```bash
   pip install httpx==0.28.1
   ```

   Note: `google-genai` requires `httpx>=0.28.1`, but the original requirements had `0.27.2`.

4. **google-resumable-media Error**: If you encounter a version error, make sure the version is correct

   ```bash
   pip install google-resumable-media==2.7.2
   ```

   Note: There was a typo in earlier versions that specified `2.72.0` instead of `2.7.2`.

5. **API Key Error**: Ensure your Gemini API key is properly set

   ```bash
   export GEMINI_API_KEY="your-api-key"
   ```

6. **Model Not Found**: Make sure you're using a supported model:

   - `gemini-2.5-flash-preview-tts`
   - `gemini-2.5-pro-preview-tts`

7. **Audio Merge Errors**: The provider will log merge issues and fallback to the first chunk

### Debug Logging

Enable debug logging to see detailed information:

```python
import logging
logging.getLogger('podcastfy.tts.providers.gemininew').setLevel(logging.DEBUG)
```

## Performance Notes

- First API call may take longer due to model initialization
- Large texts are automatically chunked for optimal performance
- Audio merging happens in memory for efficiency
- MP3 format provides good quality and compatibility with the existing system
- Internal conversion from Gemini's PCM output to MP3 for system compatibility

## Contributing

To contribute to this provider:

1. Ensure you have the development dependencies installed
2. Add tests in the appropriate test files
3. Update documentation as needed
4. Follow the existing code style and patterns

## License

This provider is part of Podcastfy and follows the same license terms.
