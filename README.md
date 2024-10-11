# Podcastfy.ai 🎙️🤖
[![PyPi Status](https://img.shields.io/pypi/v/podcastfy)](https://pypi.org/project/podcastfy/)
[![Downloads](https://pepy.tech/badge/podcastfy)](https://pepy.tech/project/podcastfy)
[![Issues](https://img.shields.io/github/issues-raw/souzatharsis/podcastfy)](https://github.com/souzatharsis/podcastfy/issues)
[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)
![GitHub Repo stars](https://img.shields.io/github/stars/souzatharsis/podcastfy)

Transforming Multi-Sourced Text into Captivating Multi-Lingual Audio Conversations with GenAI

https://github.com/user-attachments/assets/f1559e70-9cf9-4576-b48b-87e7dad1dd0b

Podcastfy is an open-source Python package that transforms web content, PDFs, and text into engaging, multi-lingual audio conversations using GenAI. 

Unlike UI-based tools focused primarily on note-taking or research synthesis (e.g. NotebookLM ❤️), Podcastfy focuses on the programmatic and bespoke generation of engaging, conversational transcripts and audio from a multitude of text sources enabling customization and scale.

## Audio Examples 🔊

This sample collection is also [available at audio.com](https://audio.com/thatupiso/collections/podcastfy):
- [English] Youtube Video from YCombinator on LLMs: ([audio](https://audio.com/thatupiso/audio/ycombinator-llms) | [youtube](https://www.youtube.com/watch?v=eBVi_sLaYsc))
- [English] Book pdf Networks, Crowds, and Markets: [audio](https://audio.com/thatupiso/audio/networks)
- [English] Research paper on Climate Change in France: ([audio](https://audio.com/thatupiso/audio/agro-paper) | [pdf](./data/pdf/s41598-024-58826-w.pdf))
- [English] Personal website: ([audio](https://audio.com/thatupiso/audio/tharsis) | [website](https://www.souzatharsis.com))
- [English] Personal website + youtube video: ([audio](https://audio.com/thatupiso/audio/tharsis-ai) | [website](https://www.souzatharsis.com) | [youtube](https://www.youtube.com/watch?v=sJE1dE2dulg))
- [French] Website: ([audio](https://audio.com/thatupiso/audio/podcast-fr-agro) | [website](https://agroclim.inrae.fr/))
- [Portuguese-BR] News article: ([audio](https://audio.com/thatupiso/audio/podcast-thatupiso-br) | [website](https://noticias.uol.com.br/eleicoes/2024/10/03/nova-pesquisa-datafolha-quem-subiu-e-quem-caiu-na-disputa-de-sp-03-10.htm))

## Features ✨

- Generate AI-powered conversational content from multiple sources (websites, YouTube, and PDFs)
- Customizable transcript and audio generation (e.g. style, language, structure, length)
- Create podcasts from pre-existing or edited transcripts
- Support for advanced text-to-speech models (OpenAI and ElevenLabs)
- Seamless CLI and Python package integration for automated workflows
- Multi-language support for global content creation (experimental!)

## Updates 🚀

### v0.2.0 release
- Users can now customize podcast style, structure, and content
- Integration with LangChain for better LLM management
- and [more...](https://github.com/souzatharsis/podcastfy/discussions/38)

## Quickstart 💻

### Prerequisites
- Python 3.11 or higher
- `$ pip install ffmpeg` (for audio processing)

### Installation
1. Install from PyPI
  `$ pip install podcastfy`

2. Set up your [API keys](usage/config.md)

### Python
```python
from podcastfy.client import generate_podcast

audio_file = generate_podcast(urls=["<url1>", "<url2>"])
```
### CLI
```
python -m podcastfy.client --url <url1> --url <url2>
```
  
## Usage 💻

- [Python Package](podcastfy.ipynb)

- [CLI](usage/cli.md)

Experience Podcastfy with our [HuggingFace](https://huggingface.co/spaces/thatupiso/Podcastfy.ai_demo) 🤗 Spaces app for a simple URL-to-Audio demo. (Note: This UI app is less extensively tested than the Python package.)

## Customization 🔧

Podcastfy offers a range of [Conversation Customization](usage/conversation_custom.md) options to tailor your AI-generated podcasts. Whether you're creating educational content, storytelling experiences, or anything in between, these configuration options allow you to fine-tune your podcast's tone, length, and format.

## Contributing 🤝

We welcome contributions! Please submit [Issues](https://github.com/souzatharsis/podcastfy/issues) or Pull Requests. Feel free to fork the repo and create your own applications. We're excited to learn about your use cases!

## Example Use Cases 🎧🎶

1. **Content Summarization**: Busy professionals can stay informed on industry trends by listening to concise audio summaries of multiple articles, saving time and gaining knowledge efficiently.

2. **Language Localization**: Non-native English speakers can access English content in their preferred language, breaking down language barriers and expanding access to global information.

3. **Website Content Marketing**: Companies can increase engagement by repurposing written website content into audio format, providing visitors with the option to read or listen.

4. **Personal Branding**: Job seekers can create unique audio-based personal presentations from their CV or LinkedIn profile, making a memorable impression on potential employers.

5. **Research Paper Summaries**: Graduate students and researchers can quickly review multiple academic papers by listening to concise audio summaries, speeding up the research process.

6. **Long-form Podcast Summarization**: Podcast enthusiasts with limited time can stay updated on their favorite shows by listening to condensed versions of lengthy episodes.

7. **News Briefings**: Commuters can stay informed about daily news during travel time with personalized audio news briefings compiled from their preferred sources.

8. **Educational Content Creation**: Educators can enhance learning accessibility by providing audio versions of course materials, catering to students with different learning preferences.

9. **Book Summaries**: Avid readers can preview books efficiently through audio summaries, helping them make informed decisions about which books to read in full.

10. **Conference and Event Recaps**: Professionals can stay updated on important industry events they couldn't attend by listening to audio recaps of conference highlights and key takeaways.


## License

This project is licensed under the [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-nc-sa/4.0/).

## Disclaimer

This tool is designed for personal or educational use. Please ensure you have the necessary rights or permissions before using content from external sources for podcast creation. All audio content is AI-generated and it is not intended to clone real-life humans!
