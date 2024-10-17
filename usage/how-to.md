# How to

All assume you have podcastfy installed and running.

## Table of Contents

- [How to use your own voice in audio podcasts](#how-to-use-your-own-voice-in-audio-podcasts)
- [How to customize the conversation](#how-to-customize-the-conversation)


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
    "creativity": 7
}

generate_podcast(
    urls=["https://example.com/tech-news"],
    conversation_config=custom_config
)
```

For more details, checkout [conversation_custom.md](https://github.com/souzatharsis/podcastfy/blob/main/usage/conversation_custom.md).




