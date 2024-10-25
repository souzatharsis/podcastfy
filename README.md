<a name="readme-top"></a>

# Podcastfy.ai 🎙️🤖
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/souzatharsis/podcastfy/blob/main/podcastfy.ipynb)
[![PyPi Status](https://img.shields.io/pypi/v/podcastfy)](https://pypi.org/project/podcastfy/)
[![Downloads](https://pepy.tech/badge/podcastfy)](https://pepy.tech/project/podcastfy)
[![Issues](https://img.shields.io/github/issues-raw/souzatharsis/podcastfy)](https://github.com/souzatharsis/podcastfy/issues)
[![Pytest](https://github.com/souzatharsis/podcastfy/actions/workflows/python-app.yml/badge.svg)](https://github.com/souzatharsis/podcastfy/actions/workflows/python-app.yml)
[![Documentation Status](https://readthedocs.org/projects/podcastfy/badge/?version=latest)](https://podcastfy.readthedocs.io/en/latest/?badge=latest)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
![GitHub Repo stars](https://img.shields.io/github/stars/souzatharsis/podcastfy)


An Open Source alternative to NotebookLM's podcast feature: Transforming Multimodal Content into Captivating Multilingual Audio Conversations with GenAI

https://github.com/user-attachments/assets/f1559e70-9cf9-4576-b48b-87e7dad1dd0b

Podcastfy is an open-source Python package that transforms multi-modal content (text, images) into engaging, multi-lingual audio conversations using GenAI. Input content include websites, PDFs, youtube videos as well as images.

Unlike UI-based tools focused primarily on note-taking or research synthesis (e.g. NotebookLM ❤️), Podcastfy focuses on the programmatic and bespoke generation of engaging, conversational transcripts and audio from a multitude of multi-modal sources enabling customization and scale.

[![Star History Chart](https://api.star-history.com/svg?repos=souzatharsis/podcastfy&type=Date&theme=dark)](https://api.star-history.com/svg?repos=souzatharsis/podcastfy&type=Date&theme=dark)

## Audio Examples 🔊
This sample collection is also [available at audio.com](https://audio.com/thatupiso/collections/podcastfy).

### Images

| Image Set | Description | Audio |
|:--|:--|:--|
| <img src="data/images/Senecio.jpeg" alt="Senecio, 1922 (Paul Klee)" width="20%" height="auto"> <img src="data/images/connection.jpg" alt="Connection of Civilizations (2017) by Gheorghe Virtosu " width="21.5%" height="auto"> | Senecio, 1922 (Paul Klee) and Connection of Civilizations (2017) by Gheorghe Virtosu  | [<span style="font-size: 25px;">🔊</span>](https://audio.com/thatupiso/audio/output-file-abstract-art) |
| <img src="data/images/japan_1.jpg" alt="The Great Wave off Kanagawa, 1831 (Hokusai)" width="20%" height="auto"> <img src="data/images/japan2.jpg" alt="Takiyasha the Witch and the Skeleton Spectre, c. 1844 (Kuniyoshi)" width="21.5%" height="auto"> | The Great Wave off Kanagawa, 1831 (Hokusai) and Takiyasha the Witch and the Skeleton Spectre, c. 1844 (Kuniyoshi) | [<span style="font-size: 25px;">🔊</span>](https://audio.com/thatupiso/audio/output-file-japan) |
| <img src="data/images/taylor.png" alt="Taylor Swift" width="28%" height="auto"> <img src="data/images/monalisa.jpeg" alt="Mona Lisa" width="10.5%" height="auto"> | Pop culture icon Taylor Swift and Mona Lisa, 1503 (Leonardo da Vinci) | [<span style="font-size: 25px;">🔊</span>](https://audio.com/thatupiso/audio/taylor-monalisa) |

### Text
| Content Type | Description | Audio | Source |
|--------------|-------------|-------|--------|
| Youtube Video | YCombinator on LLMs | [Audio](https://audio.com/thatupiso/audio/ycombinator-llms) | [YouTube](https://www.youtube.com/watch?v=eBVi_sLaYsc) |
| PDF | Book: Networks, Crowds, and Markets | [Audio](https://audio.com/thatupiso/audio/networks) | book pdf |
| Research Paper | Climate Change in France | [Audio](https://audio.com/thatupiso/audio/agro-paper) | [PDF](./data/pdf/s41598-024-58826-w.pdf) |
| Website | My Personal Website | [Audio](https://audio.com/thatupiso/audio/tharsis) | [Website](https://www.souzatharsis.com) |
| Website + YouTube | My Personal Website + YouTube Video on AI | [Audio](https://audio.com/thatupiso/audio/tharsis-ai) | [Website](https://www.souzatharsis.com), [YouTube](https://www.youtube.com/watch?v=sJE1dE2dulg) |

### Multi-Lingual Text
| Language | Content Type | Description | Audio | Source |
|----------|--------------|-------------|-------|--------|
| French | Website | Agroclimate research information | [Audio](https://audio.com/thatupiso/audio/podcast-fr-agro) | [Website](https://agroclim.inrae.fr/) |
| Portuguese-BR | News Article | Election polls in São Paulo | [Audio](https://audio.com/thatupiso/audio/podcast-thatupiso-br) | [Website](https://noticias.uol.com.br/eleicoes/2024/10/03/nova-pesquisa-datafolha-quem-subiu-e-quem-caiu-na-disputa-de-sp-03-10.htm) |

## Features ✨

- Generate conversational content from multiple-sources and formats (images, websites, YouTube, and PDFs)
- Customize transcript and audio generation (e.g. style, language, structure, length)
- Create podcasts from pre-existing or edited transcripts
- Support for advanced text-to-speech models (OpenAI, ElevenLabs and Edge)
- Support for running local llms for transcript generation (increased privacy and control)
- Seamless CLI and Python package integration for automated workflows
- Multi-language support for global content creation (experimental!)

## Updates 🚀

### v0.2.3 release
- Add support for running LLMs locally
- Enable config for running podcastfy with no API KEYs
- and [more...](https://github.com/souzatharsis/podcastfy/blob/main/CHANGELOG.md#023---2024-10-15)

### v0.2.2 release
- Podcastfy is now multi-modal! Users can generate audio from images + text inputs!

### v0.2.0 release
- Users can now customize podcast style, structure, and content
- Integration with LangChain for better LLM management

## Quickstart 💻

### Prerequisites
- Python 3.11 or higher
- `$ pip install ffmpeg` (for audio processing)

### Setup
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

- [Python Package Quickstart](podcastfy.ipynb)

- [API Reference Manual](https://podcastfy.readthedocs.io/en/latest/podcastfy.html)

- [CLI](usage/cli.md)

- [How to](usage/how-to.md)

Experience Podcastfy with our [HuggingFace](https://huggingface.co/spaces/thatupiso/Podcastfy.ai_demo) 🤗 Spaces app for a simple URL-to-Audio demo. (Note: This UI app is less extensively tested and capable than the Python package.)

## Customization 🔧

Podcastfy offers a range of customization options to tailor your AI-generated podcasts:
- Customize podcast [Conversation](usage/conversation_custom.md) (e.g. format, style, voices)
- Choose to run [Local LLMs](usage/local_llm.md) (156+ HuggingFace models)
- Set [System Settings](usage/config_custom.md) (e.g. output directory settings)

## License

This software is licensed under [Apache 2.0](LICENSE). [Here](usage/license-guide.md) are a few instructions if you would like to use podcastfy in your software.

## Contributing 🤝

We welcome contributions! See [Guidelines](GUIDELINES.md) for more details.

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

## Contributors

<a href="https://github.com/souzatharsis/podcastfy/graphs/contributors">
  <img alt="contributors" src="https://contrib.rocks/image?repo=souzatharsis/podcastfy"/>
</a>

## Disclaimer

This tool is designed for personal or educational use. Please ensure you have the necessary rights or permissions before using content from external sources for podcast creation. All audio content is AI-generated and it is not intended to clone real-life humans!

<p align="right" style="font-size: 14px; color: #555; margin-top: 20px;">
    <a href="#readme-top" style="text-decoration: none; color: #007bff; font-weight: bold;">
        ↑ Back to Top ↑
    </a>
</p>
