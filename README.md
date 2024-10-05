# Podcastfy
[![CodeFactor](https://www.codefactor.io/repository/github/souzatharsis/podcastfy/badge)](https://www.codefactor.io/repository/github/souzatharsis/podcastfy)
[![Issues](https://img.shields.io/github/issues-raw/souzatharsis/podcastfy)](https://github.com/souzatharsis/podcsatfy/issues)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)
[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

Podcastfy: Transforming Multi-Sourced Text into Captivating Multi-Lingual Audio Conversations with GenAI


https://github.com/user-attachments/assets/05f0df95-bc7c-4322-95fc-1f2e210fd513


Podcastfy is a simple LLM-based Python package and CLI tool that enables programatic creation of engaging audio podcasts from web content and text sources. Unlike tools focused primarily on note-taking or research synthesis (e.g. NotebookLM ❤️), Podcastfy specializes and focuses solely on the programatic generation of engaging, conversational audio from a multitude of text sources.

Ideal for Developers that build data-driven products for creators, educators, and researchers seeking to transform written information into easily digestible audio content. Podcastfy offers a unique solution for bridging the gap between text and audio consumption, programatically.

You can sign-up at podcastfy.me to get updates as we make improvements to the tool.

## Audio Examples

This sample collection is also [available at audio.com](https://audio.com/thatupiso/collections/podcastfy):
- (English) Research paper: ([audio](https://audio.com/thatupiso/audio/agro-paper) | [pdf](./data/pdf/s41598-024-58826-w.pdf))
- (English) Personal website: ([audio](https://audio.com/thatupiso/audio/tharsis) | [website](https://www.souzatharsis.com))
- (English) Personal website + youtube video: ([audio](https://audio.com/thatupiso/audio/tharsis-ai) | [website](https://www.souzatharsis.com) | [youtube](https://www.youtube.com/watch?v=sJE1dE2dulg))
- (French) Website: ([audio](https://audio.com/thatupiso/audio/podcast-fr-agro) | [website](https://agroclim.inrae.fr/))
- (Brazilian Portuguese) News article: ([audio](https://audio.com/thatupiso/audio/podcast-thatupiso-br) | [website](https://noticias.uol.com.br/eleicoes/2024/10/03/nova-pesquisa-datafolha-quem-subiu-e-quem-caiu-na-disputa-de-sp-03-10.htm))
  

## Features

- Generate engaging, AI-powered conversational content from multiple sources (URLs and PDFs)
- Create high-quality transcripts from diverse textual information sources
- Convert pre-existing transcript files into dynamic podcast episodes
- Support for multiple advanced text-to-speech models (OpenAI and ElevenLabs) for natural-sounding audio
- Support for multiple languages, enabling global content creation
- Seamlessly integrate CLI for streamlined workflows

## Usage

- [Python Package](podcastfy.ipynb)

- [CLI](usage/cli.md)

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
    

## Configuration

The project uses a combination of a `.env` file for managing API keys and sensitive information, and a `config.yaml` file for non-sensitive configuration settings. Follow these steps described in [Config](usage/config.md) to set up your configuration.

## Example Use Cases

1. **Content Summarization**: Busy professionals can stay informed on industry trends by listening to concise audio summaries of multiple articles, saving time and gaining knowledge efficiently.

2. **Language Localization**: Non-native English speakers can access English content in their preferred language, breaking down language barriers and expanding access to global information.

3. **Website Content Marketing**: Companies can increase engagement by repurposing written website content into audio format, providing visitors with the option to read or listen.

4. **Personal Branding**: Job seekers can create unique audio-based personal presentations from their CV or LinkedIn profile, making a memorable impression on potential employers.

5. **Research Paper Summaries**: Graduate students and researchers can quickly review multiple academic papers by listening to concise audio summaries, speeding up the research process.

6. **Long-form Podcast Summarization**: Podcast enthusiasts with limited time can stay updated on their favorite shows by listening to condensed versions of lengthy episodes.

7. **News Briefings**: Commuters can stay informed about daily news during travel time with personalized audio news briefings compiled from their preferred sources.

8. **Educational Content Creation**: Educators can enhance learning accessibility by providing audio versions of course materials, catering to students with different learning styles.

9. **Book Summaries**: Avid readers can preview books efficiently through audio summaries, helping them make informed decisions about which books to read in full.

10. **Conference and Event Recaps**: Professionals can stay updated on important industry events they couldn't attend by listening to audio recaps of conference highlights and key takeaways.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. But even more excitingly feel free to fork the repo and create your own app! Please let me know if I could be of help.

## License

This project is licensed under the [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-nc-sa/4.0/).

## Disclaimer

This tool is designed for personal or educational use. Please ensure you have the necessary rights or permissions before using content from external sources for podcast creation. All audio content is AI-generated and it is not intended to clone real-life humans!
