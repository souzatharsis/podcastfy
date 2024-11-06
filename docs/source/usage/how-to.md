# How to

All assume you have podcastfy installed and running.

## Table of Contents

- [Custom LLM Support](#custom-llm-support)
- [Running Local LLMs](#running-local-llms)
- [How to use your own voice in audio podcasts](#how-to-use-your-own-voice-in-audio-podcasts)
- [How to customize the conversation](#how-to-customize-the-conversation)
- [How to generate multilingual content](#how-to-generate-multilingual-content)
- [How to steer the conversation](#how-to-steer-the-conversation)


## Custom LLM Support

Podcastfy offers a range of LLM models for generating transcripts including OpenAI, Anthropic, Google as well as local LLM models.

### Cloud-based LLMs

By default, Podcastfy uses Google's `gemini-1.5-pro-latest` model. To select a particular cloud-based LLM model, users can pass the `llm_model_name` and `api_key_label` parameters to the `generate_podcast` function.

For example, to use OpenAI's `gpt-4-turbo` model, users can pass `llm_model_name="gpt-4-turbo"` and `api_key_label="OPENAI_API_KEY"`.

```python
audio_file = generate_podcast(
    urls=["https://en.wikipedia.org/wiki/Artificial_intelligence"],
    llm_model_name="gpt-4-turbo",
    api_key_label="OPENAI_API_KEY"
)
```

Remember to have the correct API key label and value in your environment variables (`.env` file).

### Running Local LLMs

See [local_llm.md](local_llm.md) for more details.

## How to use your own voice in audio podcasts

You just need to use ElevenLabs TSS backend and pass a custom config to use your voice instead of podcastfy's default:
  
1. Create elevenlabs account, get and [set up](https://github.com/souzatharsis/podcastfy/blob/main/usage/config.md) eleven labs API KEY

2. Clone your voice on elevenlabs website (let's say its name is 'Robbert')

4. Create custom conversation config (let's call it custom_config.yaml) to use your voice name instead of the default as described [here](https://github.com/souzatharsis/podcastfy/blob/main/usage/conversation_custom.md#text-to-speech-tts-settings). Set either question or answer voice below to 'Robbert' in elevenlabs > default_voices.

6. Run podcastfy with tts-model param as elevenlabs

CLI
   ```
   python -m podcastfy.client --url https://example.com/article1 --url https://example.com/article2 --tts-model elevenlabs --conversation-config path/to/custom_config.yaml
   ```
For Python example, checkout Customization section at [python notebook](https://github.com/souzatharsis/podcastfy/blob/main/podcastfy.ipynb).

## How to customize the conversation

You can customize the conversation by passing a custom [conversation_config.yaml](https://github.com/souzatharsis/podcastfy/blob/main/podcastfy/conversation_config.yaml) file to the CLI: 

```
python -m podcastfy.client --url https://example.com/article1 --url https://example.com/article2 --tts-model elevenlabs --conversation-config path/to/custom_config.yaml
```

You can also pass a dictionary with the custom config to the python interface generate_podcast function:

```python
from podcastfy.client import generate_podcast

custom_config = {
    "word_count": 200,
    "conversation_style": ["casual", "humorous"],
    "podcast_name": "Tech Chuckles",
    "creativity": 0.7
}

generate_podcast(
    urls=["https://example.com/tech-news"],
    conversation_config=custom_config
)
```
For more details, checkout [conversation_custom.md](https://github.com/souzatharsis/podcastfy/blob/main/usage/conversation_custom.md).

## How to generate multilingual content

In order to generate transcripts in a target language, simply set `output_language` = your target language. See [How to customize the conversation](#how-to-customize-the-conversation) on how to pass custom configuration to podcastfy. Set --transcript-only to get only the transcript without audio generation.

In order to generation audio, you can simply use openai TTS model which by default is multilingual. However, in my experience OpenAI's TTS multilingual quality is subpar. Instead, consdier using elevenlabs backend. See [How to use your own voice in audio podcasts](#how-to-use-your-own-voice-in-audio-podcasts) but instead of using your own voice you should download and set a voice in your target language for it to work.

Sample audio:
- [French](https://github.com/souzatharsis/podcastfy/blob/main/data/audio/podcast_FR_AGRO.mp3)
- [Portugue-BR](https://github.com/souzatharsis/podcastfy/blob/main/data/audio/podcast_thatupiso_BR.mp3)

The PT-BR audio actually uses my own cloned voice as AI Host 2.


## How to steer the conversation

You can guide the conversation focus and topics by setting the `user_instructions` parameter in your custom configuration. This allows you to provide specific instructions to the AI hosts about what aspects they should emphasize or explore.

Things to try:
- Focus on a specific topic (e.g. "Focus the discussion on key capabilities and limitations of modern AI models")
- Target a specific audience (e.g. "Explain concepts in a way that's accessible to someone new to Computer Science")

For example, using the CLI with a custom YAML:

```yaml
user_instructions: "Make connections with quantum computing"
```

```
python -m podcastfy.client --url https://en.wikipedia.org/wiki/Artificial_intelligence --conversation-config path/to/custom_config.yaml
```




