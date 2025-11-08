# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-11-08

### Added
- Initial release of Serpex Haystack integration
- `SerpexWebSearch` component for web search functionality
- Support for multiple search engines: Google, Bing, DuckDuckGo, Brave, Yahoo, Yandex
- Time range filtering for search results
- Automatic retry logic with exponential backoff
- Runtime parameter override capability
- Comprehensive test suite
- Full documentation and examples
- Type hints and type safety
- Haystack 2.0+ compatibility

### Features
- Multi-engine web search support
- Rich result metadata (title, URL, snippet, position)
- Configurable timeout and retry attempts
- Environment variable support for API keys
- Seamless integration with Haystack pipelines
- RAG pipeline examples
- Agent integration examples
