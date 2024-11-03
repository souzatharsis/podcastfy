---
title: 'Podcastfy: An Open-Source Framework for Transforming Multimodal Content into AI-Generated Audio Conversations'
tags:
  - Python
  - artificial intelligence
  - text-to-speech
  - multimodal
  - content transformation
  - accessibility
authors:
  - name: Tharsis T. P. Souza
    orcid: 0000-0003-3260-9526
    affiliation: 1
affiliations:
  - name: Columbia University in the City of New York
    index: 1
  - name: Instituto Federal de Educacao, Ciencia e Tecnologia do Sul de Minas (IFSULDEMINAS)
    index: 2
date: 11/01/2024
bibliography: paper.bib
---

# Abstract

Podcastfy is an open-source Python framework that enables programmatic summarization of multisourced multimodal content into multilingual natural-sounding conversations using generative AI. By enabling the transformation of various types of digital content into conversational content, Podcastfy improves accessibility, engagement, and usability for a wide range of users. The open-source nature of the project allows it to be continuously improved and adapted to meet the evolving needs of its users.

# Statement of Need

The rapid expansion of digital content across various formats has intensified the need for tools capable of converting diverse information into accessible and digestible forms \citep{johnson2023adaptive, chen2023digital, mccune2023accessibility}.. Existing solutions often fall short due to their proprietary nature, limited multimodal support, or inadequate accessibility features \citep{marcus2019design, peterson2023web, gupta2023advances}.

Podcastfy addresses this gap with an open-source solution that supports multimodal input processing and generates natural-sounding, summarized conversational content. Leveraging advances in large language models (LLMs) and text-to-speech (TTS) synthesis, Podcastfy aims to benefit a diverse group of users — including content creators, educators, researchers, and accessibility advocates — by providing a customizable solution that transforms digital content into multilingual textual and auditory formats, enhancing accessibility and engagement.

# Features

- Generate conversational content from multiple sources and formats (images, websites, YouTube, and PDFs).
- Customize transcript and audio generation (e.g., style, language, structure, length).
- Create podcasts from pre-existing or edited transcripts.
- Leverage cloud-based and local LLMs for transcript generation (increased privacy and control).
- Integrate with advanced text-to-speech models (OpenAI, ElevenLabs, and Microsoft Edge).
- Provide multi-language support for global content creation.
- Integrate seamlessly with CLI and Python packages for automated workflows.

See the [Appendix](#appendix) section for audio samples.

# Use Cases

Podcastfy is designed to serve a wide range of applications, including:

- **Content Creators** can use Podcastfy to convert blog posts, articles, or multimedia content into podcast-style audio, enabling them to reach broader audiences. By transforming content into an audio format, creators can cater to users who prefer listening over reading.

- **Educators** can transform lecture notes, presentations, and visual materials into audio conversations, making educational content more accessible to students with different learning preferences. This is particularly beneficial for students with visual impairments or those who have difficulty processing written information.

- **Researchers** can convert research papers, visual data, and technical content into conversational audio. This makes it easier for a wider audience, including those with disabilities, to consume and understand complex scientific information. Researchers can also create audio summaries of their work to enhance accessibility.

- **Accessibility Advocates** can use Podcastfy to promote digital accessibility by providing a tool that converts multimodal content into auditory formats. This helps individuals with visual impairments, dyslexia, or other disabilities that make it challenging to consume written or visual content.


# Implementation and Architecture

Podcastfy implements a modular architecture designed for flexibility and extensibility through five main components, as shown in Figure 1.

![Podcastfy's architecture and workflow diagram showing the main components and their interactions.](podcastfy.png)

*Figure 1: Podcastfy's architecture and workflow diagram showing the main components and their interactions.*

1. **Client Interface**
   - Provides both CLI (Command-Line Interface) and API interfaces.
   - Coordinates the workflow between processing layers.
   - Implements a unified interface for podcast generation through the `generate_podcast()` method.

2. **Configuration Management**
   - Offers extensive customization options through a dedicated module.
   - Manages system settings and user preferences, such as podcast name, language, style, and structure.
   - Controls the behavior of all processing layers.

3. **Content Extraction Layer**
   - Extracts content from various sources, including websites, PDFs, and YouTube videos.
   - The `ContentExtractor` class coordinates three specialized extractors:
     - `PDFExtractor`: Handles PDF document processing.
     - `WebsiteExtractor`: Manages website content extraction.
     - `YouTubeTranscriber`: Processes YouTube video content.
   - Serves as the entry point for all input types, providing standardized text output to the transcript generator.

4. **LLM-based Transcript Generation Layer**
   - Uses large language models to generate natural-sounding conversations from extracted content.
   - The `ContentGenerator` class manages conversation generation using different LLM backends:
     - Integrates with LangChain to implement prompt management and common LLM access through the `BaseChatModel` interface.
     - Supports both local (`LlamaFile`) and cloud-based models.
     - Uses `ChatGoogleGenerativeAI` for cloud-based LLM services.
   - Allows customization of conversation style, roles, and dialogue structure.
   - Outputs structured conversations in text format.

5. **Text-to-Speech (TTS) Layer**
   - Converts input transcripts into audio using various TTS models.
   - The `TextToSpeech` class implements a factory pattern:
     - The `TTSFactory` creates appropriate providers based on configuration.
     - Supports multiple backends (OpenAI, ElevenLabs, and Microsoft Edge) through the `TTSProvider` interface.
   - Produces the final podcast audio output.

The modular architecture enables independent development and maintenance of each component. This pipeline design ensures a clean separation of concerns while maintaining seamless data transformation between stages. This modular approach also facilitates easy updates and extensions to individual components without affecting the rest of the system.

The framework is offered as a Python package, with a command-line interface as well as a REST API, making it accessible to users with different technical backgrounds and requirements.


# Quick Start

## Prerequisites
- Python 3.11 or higher
- `$ pip install ffmpeg` (for audio processing)

## Setup
1. Install from PyPI
  `$ pip install podcastfy`

2. Set up [API keys](usage/config.md)

## Python
```python
from podcastfy.client import generate_podcast

audio_file = generate_podcast(urls=["<url1>", "<url2>"])
```
## CLI
```
python -m podcastfy.client --url <url1> --url <url2>
```


# Customization Examples

Podcastfy offers various customization options that make it versatile for different types of content transformation. Below are some examples that demonstrate its capabilities.

## Academic Debate

The following Python code demonstrates how to configure Podcastfy for an academic debate:

```python
from podcastfy import generate_podcast

debate_config = {
    "conversation_style": ["formal", "debate"],
    "roles_person1": "main presenter",
    "roles_person2": "opposing viewpoint", 
    "dialogue_structure": ["Introduction", "Argument Presentation", "Counterarguments", "Conclusion"]
}

generate_podcast(
    urls=["PATH/TO/academic-article.pdf"],
    conversation_config=debate_config
)
```

In this example, the roles are set to "main presenter" and "opposing viewpoint" to simulate an academic debate between two speakers on a chosen topic. This approach is especially useful for educational content that aims to present multiple perspectives on a topic. The output is structured with clear sections such as introduction, argument presentation, counterarguments, and conclusion, allowing listeners to follow complex ideas easily.

## Storytelling Adventure

The following Python code demonstrates how to generate a storytelling podcast:

```python
from podcastfy import generate_podcast

story_config = {
    "conversation_style": ["adventurous", "narrative"],
    "creativity": 1.0,
    "roles_person1": "narrator", 
    "roles_person2": "character",
    "dialogue_structure": ["Introduction", "Adventure Begins", "Challenges", "Resolution"]
}

generate_podcast(
    urls=["SAMPLE/WWW.URL.COM"],
    conversation_config=story_config
)
```

In this example, Podcastfy creates an engaging story by assigning roles like "narrator" and "character" and adjusting the creativity parameter for richer descriptions. Using this configuration, Podcastfy can generate engaging narrative content. By adjusting the creativity parameter, Podcastfy can create a story involving multiple characters, unexpected plot twists, and rich descriptions.

## Additional Examples

### Daily News Briefing
```python
news_config = {
    "word_count": 1500,
    "conversation_style": ["concise", "informative"],
    "podcast_name": "Morning Briefing",
    "dialogue_structure": [
        "Headlines",
        "Key Stories",
        "Market Update",
        "Weather"
    ],
    "roles_person1": "news anchor",
    "roles_person2": "field reporter",
    "creativity": 0.3
}

generate_podcast(
    urls=[
        "https://news-source.com/headlines",
        "https://market-updates.com/today"
    ],
    conversation_config=news_config
)
```

### Language Learning Content
```python
language_config = {
    "output_language": "Spanish",
    "word_count": 1000,
    "conversation_style": ["educational", "casual"],
    "engagement_techniques": [
        "vocabulary explanations",
        "cultural context",
        "pronunciation tips"
    ],
    "roles_person1": "language teacher",
    "roles_person2": "curious student",
    "creativity": 0.6
}

generate_podcast(
    urls=["https://spanish-content.com/article"],
    conversation_config=language_config
)
```

### Technical Tutorial
```python
tutorial_config = {
    "word_count": 2500,
    "conversation_style": ["instructional", "step-by-step"],
    "roles_person1": "expert developer",
    "roles_person2": "learning developer",
    "dialogue_structure": [
        "Concept Introduction",
        "Technical Background",
        "Implementation Steps",
        "Common Pitfalls",
        "Best Practices"
    ],
    "engagement_techniques": [
        "code examples",
        "real-world applications",
        "troubleshooting tips"
    ],
    "creativity": 0.4
}

generate_podcast(
    urls=["https://tech-blog.com/tutorial"],
    conversation_config=tutorial_config
)
```

## Working with Podcastfy Modules

Podcastfy's components are designed to work independently, allowing flexibility in updating or extending each module. The data flows from the Content Extractor to the Content Generator and finally to the Text-to-Speech Converter, ensuring a seamless transformation of multimodal content into audio. In this section, we provide some examples of how to use each module.

## Content Extraction
Podcastfy's `content_extractor.py` module allows users to extract content from a given URL, which can be processed further to generate a podcast. Below is an example of how to use the content extraction component:

```python
from podcastfy.content_extractor import ContentExtractor

# Initialize the content extractor
extractor = ContentExtractor()

# Extract content from a URL
url = "https://example.com/article"
extracted_content = extractor.extract_content(url)

print("Extracted Content:")
print(extracted_content)
```

This example demonstrates how to extract text from a given URL. The extracted content is then passed to the next stages of processing.

## Content Generation

The `content_generator.py` module is responsible for generating conversational content based on textual input. Below is an example of how to use the content generation component:

```python
from podcastfy.content_generator import ContentGenerator

# Initialize the content generator
generator = ContentGenerator(api_key="<GEMINI_API_KEY>")

# Generate conversational content
input_text = "This is a sample input text about artificial intelligence."
generated_conversation = generator.generate_conversation(input_text)

print("Generated Conversation:")
print(generated_conversation)
```

In this example, the `ContentGenerator` class is used to create a conversation based on an input text. This generated conversation can be customized by setting different parameters, such as conversation style and roles. Users can opt to run a cloud-based LLM (Gemini) or run a local (potentially Open Source) LLM model by setting the `is_local` parameter to `True` ([see local llm configuration](https://github.com/souzatharsis/podcastfy/blob/main/usage/local_llm.md)).

## Text-to-Speech Conversion

The `text_to_speech.py` module allows the generated text to be converted into audio. Below is an example of how to use the text-to-speech component:

```python
from podcastfy.text_to_speech import TextToSpeech

# Initialize the text-to-speech converter
tts = TextToSpeech(model='elevenlabs', api_key="<ELEVENLABS_API_KEY>")

# Convert the generated conversation to speech
input_text = "<Person1>This is a sample conversation generated by Podcastfy.</Person1><Person2>That's great!</Person2>"
output_audio_file = "output_podcast.mp3"
tts.convert_to_speech(input_text, output_audio_file)

print(f"Audio saved to {output_audio_file}")
```

This example demonstrates how to use the `TextToSpeech` class to convert generated text into an audio file. Users can specify different models for TTS, such as `elevenlabs`, `openai`, or `edge` (free to use).

## Full Pipeline Example

To demonstrate the complete usage of Podcastfy, here is an example that combines content extraction, content generation, and text-to-speech conversion:

```python
from podcastfy.content_extractor import ContentExtractor
from podcastfy.content_generator import ContentGenerator
from podcastfy.text_to_speech import TextToSpeech

# Step 1: Extract content from a URL
extractor = ContentExtractor()
url = "https://example.com/article"
extracted_content = extractor.extract_content(url)

# Step 2: Generate conversational content based on the extracted content
generator = ContentGenerator()
generated_conversation = generator.generate_conversation(extracted_content)

# Step 3: Convert the generated conversation into an audio podcast
tts = TextToSpeech(model='elevenlabs')
output_audio_file = "output_podcast.mp3"
tts.convert_to_speech(generated_conversation, output_audio_file)

print(f"Podcast saved to {output_audio_file}")
```

This full pipeline example shows how Podcastfy can be used end-to-end to transform content from a web page into an audio podcast. Each step uses different modules of Podcastfy, providing a complete solution for multimodal content transformation. The `generate_podcast()` method from `client.py` encapsulates this end-to-end workflow in a simple to use unified interface.

# Community and Development

Podcastfy is actively maintained and welcomes community contributions. The project follows best practices for open-source development, including:

- Comprehensive documentation
- Clear contribution guidelines
- Automated testing
- Continuous integration
- Version control
- Issue tracking

Podcastfy is distributed under an open-source license (Apache 2.0) to ensure that it is freely available to the community. The source code, along with detailed documentation, installation instructions, and usage examples, can be found in our [GitHub repository](https://github.com/souzatharsis/podcastfy). The repository includes comprehensive guidelines on how to set up the framework, as well as a collection of tutorials to help users get started with transforming multimodal content into audio conversations.

# Limitations

Podcastfy has several limitations, including:

## Content Accuracy and Quality

- The accuracy of generated conversations depends heavily on the capabilities of the underlying LLMs.
- Complex technical or domain-specific content may not always be accurately interpreted or summarized.
- The framework cannot guarantee the factual correctness of generated content, requiring human verification for critical applications.

## Language Support Constraints

- While multilingual support is available, performance may vary significantly across different languages.
- Less common languages may have limited TTS voice options and lower-quality speech synthesis.
- Nuanced cultural contexts and idioms may not translate effectively across languages.

## Technical Dependencies

- Reliance on third-party APIs (OpenAI, ElevenLabs, Google) introduces potential service availability risks.
- Local LLM options, while providing independence, require significant computational resources.
- Network connectivity is required for cloud-based services, limiting offline usage.

## Content Extraction Challenges

- Complex webpage layouts or dynamic content may not be accurately extracted.
- PDF extraction quality depends on document formatting and structure.
- YouTube video processing depends on the availability of transcripts.

## Accessibility Considerations

- Generated audio may not fully meet all accessibility standards.
- Limited support for real-time content processing.
- May require additional processing for users with specific accessibility needs.

These limitations highlight areas for future development and improvement of the framework. Users should carefully consider these constraints when implementing Podcastfy for their specific use cases and requirements.


# Conclusion

Podcastfy contributes to multimodal content accessibility by enabling the programmatic transformation of digital content into conversational audio. The framework addresses accessibility needs through automated content summarization and natural-sounding speech synthesis. Its modular design and configurable options allow for flexible content processing and audio generation workflows that can be adapted for different use cases and requirements.

As an open-source project, Podcastfy benefits from continuous community-driven improvements and adaptations, helping support its long-term value and relevance in meeting evolving user requirements and accessibility standards.

We invite contributions from the community to further enhance the capabilities of Podcastfy. Whether it's by adding support for new input modalities, improving the quality of conversation generation, or optimizing the TTS synthesis, we welcome collaboration to make Podcastfy more powerful and versatile.

# Acknowledgements

Add acknowledgements for contributors as well as eventual reviewers.

We acknowledge the open-source community and the developers of the various libraries and tools that make Podcastfy possible. Special thanks to the developers of LangChain, Llamafile, Gemini, OpenAI, ElevenLabs, and Microsoft Edge for their tools and documentation.


# Appendix

## Audio Examples
This sample collection is also [available at audio.com](https://audio.com/thatupiso/collections/podcastfy).

### Images

| Image Set | Description | Audio |
|:--|:--|:--|
| <img src="../data/images/Senecio.jpeg" alt="Senecio, 1922 (Paul Klee)" width="20%" height="auto"> <img src="../data/images/connection.jpg" alt="Connection of Civilizations (2017) by Gheorghe Virtosu " width="21.5%" height="auto"> | Senecio, 1922 (Paul Klee) and Connection of Civilizations (2017) by Gheorghe Virtosu  | [<span style="font-size: 25px;">🔊</span>](https://audio.com/thatupiso/audio/output-file-abstract-art) |
| <img src="../data/images/japan_1.jpg" alt="The Great Wave off Kanagawa, 1831 (Hokusai)" width="20%" height="auto"> <img src="../data/images/japan2.jpg" alt="Takiyasha the Witch and the Skeleton Spectre, c. 1844 (Kuniyoshi)" width="21.5%" height="auto"> | The Great Wave off Kanagawa, 1831 (Hokusai) and Takiyasha the Witch and the Skeleton Spectre, c. 1844 (Kuniyoshi) | [<span style="font-size: 25px;">🔊</span>](https://audio.com/thatupiso/audio/output-file-japan) |
| <img src="../data/images/taylor.png" alt="Taylor Swift" width="28%" height="auto"> <img src="../data/images/monalisa.jpeg" alt="Mona Lisa" width="10.5%" height="auto"> | Pop culture icon Taylor Swift and Mona Lisa, 1503 (Leonardo da Vinci) | [<span style="font-size: 25px;">🔊</span>](https://audio.com/thatupiso/audio/taylor-monalisa) |

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

# References
