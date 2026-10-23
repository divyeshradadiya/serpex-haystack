# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] - 2026-10-23

### Changed
- Calls the API through the official `serpex` SDK (`>=2.11.0,<3`) instead of its own `httpx` code, so parameters, timeouts and error parsing cannot drift from the API. Results are typed (`serpex.SearchResponse`). `httpx` is no longer a direct dependency.
- A failed request now raises `SerpexError` (a Haystack `ComponentError`) with one actionable sentence per HTTP status (400, 401 check `SERPEX_API_KEY`, 402 out of credits, 429 retry after N ms with the plan limit, 5xx temporary and not charged) plus `status_code`, `details` and `retryable`. Before, the raw `httpx.HTTPStatusError` / `httpx.RequestError` propagated; code that caught those must catch `SerpexError`.
- Retries (429, 5xx, transport errors) are unchanged; 4xx still fails on the first attempt.
- `User-Agent: serpex-python/<sdk> serpex-haystack/1.1.1`.

### Fixed
- README: the "Time Filters" feature was listed although `time_range` is ignored by the API; date filters are `after:` / `before:` operators in the query.

### Tests
- Offline tests against recorded API responses (`tests/fixtures/`), covering results, page content, content errors, empty results, retries and every error status.

## [1.1.0] - 2026-10-01

### Added
- `include_content` / `content_results` (5 or 10), in `__init__` and per call in `run()`: each Document carries the page content (markdown) in `content`, with the snippet in `meta["snippet"]`; a page that can't be extracted keeps the snippet and carries `meta["content_error"]`.
- Every request sends `User-Agent: serpex-haystack/<version>`.

### Changed
- Only `q` (plus the content options) is sent. `engine` (`__init__`, `run()`) and `time_range` (`run()`) are still accepted but emit a `DeprecationWarning` and are not sent; `category=web` is no longer sent. Removed in 2.0.
- `engine` is no longer written by `to_dict()`; pipelines saved with it still load (`from_dict()` drops it). `meta["engine"]` is always `"auto"` (deprecated, removed in 2.0).
- Default timeout 10 s → 60 s (100 s with `include_content`): 10 s was shorter than the server's own search budget, so slow searches failed client-side after being billed.
- Retries only on transport errors, 429 and 5xx; 4xx (400/401/402/403) fail immediately instead of being retried.

## [1.0.1] - 2026-09-22

### Changed
- docs: positioning — Serpex is a real-time web search API; README, integration page, docstrings, examples and package metadata updated.
- `engine` deprecated (ignored by the API since 2026-06). Still accepted in `__init__`, `run()` and saved pipelines; its type hint is now `str` (was a `Literal` of engine names — any value that type-checked before still does) and its default is now `"auto"` (the API ignores it either way). `Document.meta["engine"]` is kept.

### Removed
- The engine-comparison example and the internal structure-comparison note.

## [1.0.0] - 2024-11-08

### Added
- Initial release of Serpex Haystack integration
- `SerpexWebSearch` component for web search functionality
- Real-time web search via the Serpex API
- Time range filtering for search results
- Automatic retry logic with exponential backoff
- Runtime parameter override capability
- Comprehensive test suite
- Full documentation and examples
- Type hints and type safety
- Haystack 2.0+ compatibility

### Features
- Web search support
- Rich result metadata (title, URL, snippet, position)
- Configurable timeout and retry attempts
- Environment variable support for API keys
- Seamless integration with Haystack pipelines
- RAG pipeline examples
- Agent integration examples
