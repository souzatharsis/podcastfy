# Changelog

## [0.2.3] - 2024-10-15

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
