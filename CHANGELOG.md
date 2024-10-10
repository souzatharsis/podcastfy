# Changelog

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
