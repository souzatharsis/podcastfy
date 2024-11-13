# How to

All assume you have podcastfy installed and running.

## Table of Contents

- [Custom LLM Support](#custom-llm-support)
- [Running Local LLMs](#running-local-llms)
- [How to use your own voice in audio podcasts](#how-to-use-your-own-voice-in-audio-podcasts)
- [How to customize the conversation](#how-to-customize-the-conversation)
- [How to generate multilingual content](#how-to-generate-multilingual-content)
- [How to steer the conversation](#how-to-steer-the-conversation)
- [How to generate longform podcasts](#how-to-generate-longform-podcasts)


## Custom LLM Support

Podcastfy offers a range of LLM models for generating transcripts including OpenAI, Anthropic, Google as well as local LLM models.

### Cloud-based LLMs

By default, Podcastfy uses Google's `gemini-1.5-pro-latest` model. To select a particular cloud-based LLM model, users can pass the `llm_model_name` and `api_key_label` parameters to the `generate_podcast` function. See [full list of supported models](https://docs.litellm.ai/docs/providers) for more details.

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


## How to generate longform podcasts

By default, Podcastfy generates shortform podcasts. However, users can generate longform podcasts by setting the `longform` parameter to `True`.

```python
audio_file = generate_podcast(
    urls=["https://example.com/article1", "https://example.com/article2"],
    longform=True
)
```

LLMs have a limited ability to output long text responses. Most LLMs have a `max_output_tokens` of around 4096 and 8192 tokens. Hence, long-form podcast transcript generation is challeging. We have implemented a technique I call "Content Chunking with Contextual Linking" to enable long-form podcast generation by breaking down the input content into smaller chunks and generating a conversation for each chunk while ensuring the combined transcript is coherent and linked to the original input.

By default, shortform podcasts (default configuration) generate audio of about 2-5 minutes while longform podcasts may reach 20-30 minutes.

Users may adjust lonform podcast length by setting the following parameters in your customization params (conversation_config.yaml):
- `max_num_chunks` (default: 7): Sets maximum number of rounds of discussions.
- `min_chunk_size` (default: 600): Sets minimum number of characters to generate a round of discussion.

A "round of discussion" is the output transcript obtained from a single LLM call. The higher the `max_num_chunks` and the lower the `min_chunk_size`, the longer the generated podcast will be.
Today, this technique allows the user to generate long-form podcasts of any length if input content is long enough. However, the conversation quality may decrease and its length may converge to a maximum if `max_num_chunks`/`min_chunk_size` is to high/low particularly if input content length is limited.

Current implementation limitations:
- Images are not yet supported for longform podcast generation
- Base LLM model is fixed to Gemini

Above limitations are somewhat easily fixable however we chose to make updates in smaller but quick iterations rather than making all-in changes.

