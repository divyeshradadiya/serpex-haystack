# Serpex Haystack Integration

[![PyPI - Version](https://img.shields.io/pypi/v/serpex-haystack.svg)](https://pypi.org/project/serpex-haystack)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/serpex-haystack.svg)](https://pypi.org/project/serpex-haystack)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI Tests](https://github.com/divyeshradadiya/serpex-haystack/actions/workflows/ci.yml/badge.svg)](https://github.com/divyeshradadiya/serpex-haystack/actions/workflows/ci.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[Serpex](https://serpex.dev) integration for [Haystack](https://haystack.deepset.ai/) - bringing web search to your Haystack pipelines.

## Overview

Serpex is the web search API and extract API for AI agents: ranked web results, optionally with page content as markdown. This integration allows you to seamlessly incorporate web search results into your Haystack RAG (Retrieval-Augmented Generation) pipelines and AI applications.

### Key Features

- 🔍 **Web Search**: One search engine, nothing to configure; optional page content as markdown
- ⚡ **Reliable**: Automatic retries with exponential backoff
- 🎯 **Rich Results**: Get organic search results with titles, snippets, and URLs
- 🕒 **Time Filters**: Filter results by day, week, month, or year
- 🔒 **Type-Safe**: Fully typed with comprehensive type hints
- 📝 **Haystack Native**: Seamless integration with Haystack 2.0+ components

## Installation

```bash
pip install serpex-haystack
```

## Quick Start

### Get Your API Key

Sign up at [Serpex.dev](https://serpex.dev) to get your API key.

### Basic Usage

```python
from haystack import Pipeline
from haystack.components.builders import PromptBuilder
from haystack.components.generators import OpenAIGenerator
from haystack.utils import Secret
from haystack_integrations.components.websearch.serpex import SerpexWebSearch

# Create a web search component
web_search = SerpexWebSearch(
    api_key=Secret.from_env_var("SERPEX_API_KEY"),
)

# Use it standalone
results = web_search.run(query="What is Haystack AI?")
for doc in results["documents"]:
    print(f"Title: {doc.meta['title']}")
    print(f"URL: {doc.meta['url']}")
    print(f"Snippet: {doc.content}\n")
```

### RAG Pipeline Example

```python
from haystack import Pipeline
from haystack.components.builders import PromptBuilder
from haystack.components.generators import OpenAIGenerator
from haystack.utils import Secret
from haystack_integrations.components.websearch.serpex import SerpexWebSearch

# Create a simple RAG pipeline with web search
prompt_template = """
Based on the following search results, answer the question.

Search Results:
{% for doc in documents %}
- {{ doc.meta.title }}: {{ doc.content }}
  Source: {{ doc.meta.url }}
{% endfor %}

Question: {{ query }}

Answer:
"""

pipe = Pipeline()
pipe.add_component("search", SerpexWebSearch(api_key=Secret.from_env_var("SERPEX_API_KEY")))
pipe.add_component("prompt", PromptBuilder(template=prompt_template))
pipe.add_component("llm", OpenAIGenerator(api_key=Secret.from_env_var("OPENAI_API_KEY")))

pipe.connect("search.documents", "prompt.documents")
pipe.connect("prompt", "llm")

# Run the pipeline
result = pipe.run({
    "search": {"query": "Latest developments in AI agents"},
    "prompt": {"query": "Latest developments in AI agents"}
})

print(result["llm"]["replies"][0])
```

## Advanced Features

### Page content

```python
# Each Document carries the page content (markdown) for the top 5 results;
# the snippet moves to meta["snippet"].
web_search = SerpexWebSearch(include_content=True, content_results=5)
results = web_search.run(query="AI news")

# Or per call
results = web_search.run(query="Python tutorials", include_content=True)
```

Best-effort: a page that can't be extracted keeps the snippet as `content` and
carries `meta["content_error"]`.

### Deprecated parameters

Serpex is one search engine, so there is nothing to select. `engine` (in
`__init__` and `run()`) and `time_range` (in `run()`) are deprecated and ignored
by the Serpex API. They are still accepted so existing code keeps running, emit a
`DeprecationWarning`, and are not sent. Pipelines saved with an older version
still load: their `engine` value is dropped. Removed in 2.0.

### Timeouts and retries

```python
web_search = SerpexWebSearch(
    api_key=Secret.from_env_var("SERPEX_API_KEY"),
    timeout=60.0,  # Request timeout in seconds
    retry_attempts=3  # Total attempts on a transport error, 429 or 5xx
)
```

The default timeout is 60 s (100 s with `include_content`), longer than the
server's own budget, so a slow search isn't abandoned after the server has billed
it. Only transport errors, 429 and 5xx are retried; 4xx errors (bad request,
invalid key, no credits) fail immediately.

## Component Reference

### SerpexWebSearch

A Haystack component for fetching web search results via the Serpex API.

#### Parameters

- **api_key** (`Secret`, optional): Serpex API key. Defaults to `SERPEX_API_KEY` environment variable.
- **timeout** (`float`, optional): Request timeout in seconds. Defaults to 60, or 100 with `include_content`.
- **retry_attempts** (`int`, optional): Total attempts on a transport error, 429 or 5xx. Defaults to `2`.
- **include_content** (`bool`, optional): Also fetch page content (markdown) for the top results. Defaults to `False`.
- **content_results** (`int`, optional): How many top results get content, `5` or `10`. Defaults to `5`.
- **engine** (`str`, optional): **Deprecated** — ignored by the Serpex API and not sent.

#### Inputs

- **query** (`str`): The search query string.
- **include_content** (`bool`, optional): Overrides the component setting for this call.
- **engine**, **time_range** (optional): **Deprecated** — ignored by the Serpex API and not sent.

#### Outputs

- **documents** (`List[Document]`): List of Haystack Document objects containing search results.

Each document includes:
- **content**: The page content (markdown) when `include_content` is on and the page was extracted; otherwise the snippet
- **meta**:
  - `title`: Result title
  - `url`: Result URL
  - `position`: Position in search results
  - `query`: Original search query
  - `snippet`, `content_error`: Only with `include_content`
  - `engine`: **Deprecated**, always `"auto"`; removed in 2.0

## Examples

Check out the [examples](examples/) directory for more use cases:

- [Basic Search](examples/basic_search.py)
- [RAG Pipeline](examples/rag_pipeline.py)
- [Agent with Web Search](examples/agent_example.py)

## Why Serpex?

- **🌐 Real-Time Web Search**: current results for any query, as structured JSON
- **📄 Page Content Extraction**: turn URLs into LLM-ready markdown
- **🤖 Built for AI**: made for agents, LLM tools and RAG pipelines

## Documentation

- [Serpex API Documentation](https://docs.serpex.dev)
- [Haystack Documentation](https://docs.haystack.deepset.ai)
- [Integration Examples](examples/)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Development Setup

```bash
# Clone the repository
git clone https://github.com/divyeshradadiya/serpex-haystack.git
cd serpex-haystack

# Install with development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check .
black --check .

# Run type checking
mypy src/
```

## License

This project is licensed under the Apache 2.0 License - see the [LICENSE](LICENSE) file for details.

## Support

- 📧 Email: support@serpex.dev
- 💬 Discord: [Join our community](https://discord.com/channels/1417759329385316383/1421004675343319102)
- 🐛 Issues: [GitHub Issues](https://github.com/divyeshradadiya/serpex-haystack/issues)
- 📖 Docs: [docs.serpex.dev](https://serpex.dev/docs)

## Acknowledgments

Built with ❤️ for the Haystack community by [Divyesh Radadiya](https://github.com/divyeshradadiya)

---

**Note**: This is a community-maintained integration. For Serpex API support, visit [serpex.dev](https://serpex.dev).
