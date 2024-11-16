# Changelog


## [0.4.0] - 2024-11-16

### Added
- Add Google Singlespeaker (Journey) and Multispeaker TTS models 
- Fixed limitations of Google Multispeaker TTS model: 5000 bytes input limite and 500 bytes per turn limit.
- Updated tests and docs accordingly

## [0.3.6] - 2024-11-13

### Added
- Add longform podcast generation support
  - Users can now generate longer podcasts (20-30+ minutes) using the `--longform` flag in CLI or `longform=True` in Python API
  - Implements "Content Chunking with Contextual Linking" technique for coherent long-form content
  - Configurable via `max_num_chunks` and `min_chunk_size` parameters in conversation config
  - `word_count` parameter removed from conversation config as it's no longer used

## [0.3.3] - 2024-11-08

### Breaking Changes
- Loading images from 'path' has been removed for security reasons. Please specify images by passing an 'url'.

### Added
- Add podcast generation from topic "Latest News in U.S. Politics"
- Integrate with 100+ LLM models (OpenAI, Anthropic, Google etc) for transcript generation
- Integrate with Google's Multispeaker TTS model for high-quality audio generation
- Deploy [REST API](https://github.com/souzatharsis/podcastfy/blob/main/usage/api.md) with FastAPI
- Support for raw text as input
- Add PRIVACY_POLICY.md
- Start TESTIMONIALS.md
- Add apps using Podcastfy to README.md

### Fixed
- #165 Fixed audio generation in Windows OS issue: Normalize path separators for cross-platform compatibility

## [0.2.3] - 2024-10-15

### Added
- Add local llm option by @souzatharsis
- Enable running podcastfy with no API KEYs thanks to solving #18 #58 #65 by @souzatharsis and @ChinoUkaegbu 
- Add user-provided TSS config such as voices #10 #6 #27 by @souzatharsis
- Add open in collab and setting python version to 3.11 by @Devparihar5 #57
- Add edge tts support by @ChinoUkaegbu
- Update pypdf with pymupdf(10x faster then pypdf) #56 check by @Devparihar5
- Replace r.jina.ai with simple BeautifulSoap #18 by @souzatharsis

### Fixed
- Fixed CLI for user-provided config #69 @souzatharsis

## [0.2.2] - 2024-10-13

### Added
- Added API reference docs and published it to https://podcastfy.readthedocs.io/en/latest/

### Fixed 
- ([#52](https://github.com/user/podcastfy/issues/37)) Fixed simple bug introduced in 0.2.1 that broke the ability to generate podcasts from text inputs!
- Fixed one example in the documentation that was not working.

## [0.2.1] - 2024-10-12


### Added
- ([#8](https://github.com/user/podcastfy/issues/8)) Podcastfy is now multi-modal! Users can now generate audio from images by simply providing the paths to the image files.

### Fixed 
- ([#40](https://github.com/user/podcastfy/issues/37)) Updated default ElevenLabs voice from `BrittneyHart` to `Jessica`. The latter was a non-default voice I used from my account, which caused error for users who don't have it.

## [0.2.0] - 2024-10-10

### Added
- Parameterized podcast generation with Conversation Configuration ([#11](https://github.com/user/podcastfy/issues/11), [#3](https://github.com/user/podcastfy/issues/3), [#4](https://github.com/user/podcastfy/issues/4))
  - Users can now customize podcast style, structure, and content
  - See [Conversation Customization](usage/conversation_custom.md) for detailed options
  - Updated demo in [podcastfy.ipynb](podcastfy.ipynb)
- LangChain integration for improved LLM interface and observability ([#29](https://github.com/user/podcastfy/issues/29))
- Changelog to track version updates ([#22](https://github.com/user/podcastfy/issues/22))
- Tests for Customized conversation scenarios

### Fixed
- CLI now correctly reads from user-provided local .env file ([#37](https://github.com/user/podcastfy/issues/37))
