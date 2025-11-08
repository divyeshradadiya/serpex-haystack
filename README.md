# Serpex Haystack Integration

[![PyPI - Version](https://img.shields.io/pypi/v/serpex-haystack.svg)](https://pypi.org/project/serpex-haystack)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/serpex-haystack.svg)](https://pypi.org/project/serpex-haystack)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![CI Tests](https://github.com/divyeshradadiya/serpex-haystack/actions/workflows/ci.yml/badge.svg)](https://github.com/divyeshradadiya/serpex-haystack/actions/workflows/ci.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

[Serpex](https://serpex.dev) integration for [Haystack](https://haystack.deepset.ai/) - bringing powerful multi-engine web search capabilities to your Haystack pipelines.

## Overview

Serpex is a unified web search API that provides access to multiple search engines including Google, Bing, DuckDuckGo, Brave, Yahoo, and Yandex. This integration allows you to seamlessly incorporate web search results into your Haystack RAG (Retrieval-Augmented Generation) pipelines and AI applications.

### Key Features

- 🔍 **Multi-Engine Support**: Switch between Google, Bing, DuckDuckGo, Brave, Yahoo, and Yandex
- ⚡ **High Performance**: Fast and reliable API with automatic retries
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

Sign up at [Serpex.dev](https://serpex.dev) to get your free API key.

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
    engine="google",  # or "bing", "duckduckgo", "brave", "yahoo", "yandex"
    num_results=10
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

### Multiple Search Engines

```python
# Use different engines for different queries
google_search = SerpexWebSearch(engine="google")
bing_search = SerpexWebSearch(engine="bing")
duckduckgo_search = SerpexWebSearch(engine="duckduckgo")
```

### Time Range Filtering

```python
# Get only recent results
recent_results = web_search.run(
    query="AI news",
    time_range="week"  # Options: "day", "week", "month", "year", "all"
)
```

### Runtime Configuration Override

```python
# Override settings at runtime
results = web_search.run(
    query="Python tutorials",
    engine="duckduckgo",  # Override default engine
    num_results=20  # Override default count
)
```

### Error Handling with Retries

The component includes built-in retry logic with exponential backoff:

```python
web_search = SerpexWebSearch(
    api_key=Secret.from_env_var("SERPEX_API_KEY"),
    timeout=10.0,  # Request timeout in seconds
    retry_attempts=3  # Number of retry attempts
)
```

## Component Reference

### SerpexWebSearch

A Haystack component for fetching web search results via the Serpex API.

#### Parameters

- **api_key** (`Secret`, optional): Serpex API key. Defaults to `SERPEX_API_KEY` environment variable.
- **engine** (`str`, optional): Search engine to use. Options: `"auto"`, `"google"`, `"bing"`, `"duckduckgo"`, `"brave"`, `"yahoo"`, `"yandex"`. Defaults to `"google"`.
- **num_results** (`int`, optional): Number of results to return. Defaults to `10`.
- **timeout** (`float`, optional): Request timeout in seconds. Defaults to `10.0`.
- **retry_attempts** (`int`, optional): Number of retry attempts. Defaults to `2`.

#### Inputs

- **query** (`str`): The search query string.
- **engine** (`str`, optional): Override the default search engine.
- **num_results** (`int`, optional): Override the default number of results.
- **time_range** (`str`, optional): Filter by time range (`"all"`, `"day"`, `"week"`, `"month"`, `"year"`).

#### Outputs

- **documents** (`List[Document]`): List of Haystack Document objects containing search results.

Each document includes:
- **content**: The search result snippet
- **meta**:
  - `title`: Result title
  - `url`: Result URL
  - `position`: Position in search results
  - `query`: Original search query
  - `engine`: Search engine used

## Examples

Check out the [examples](examples/) directory for more use cases:

- [Basic Search](examples/basic_search.py)
- [RAG Pipeline](examples/rag_pipeline.py)
- [Multi-Engine Comparison](examples/multi_engine.py)
- [Agent with Web Search](examples/agent_example.py)

## Why Serpex?

- **🌐 Multi-Engine Access**: One API for all major search engines
- **⚡ Fast & Reliable**: Optimized infrastructure with 99.9% uptime
- **💰 Cost-Effective**: Competitive pricing with generous free tier
- **📊 Rich Metadata**: Comprehensive result data including positions, timestamps, and more
- **🔒 Secure**: Enterprise-grade security and data privacy
- **🚀 Scalable**: Handle thousands of requests per second

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
- 💬 Discord: [Join our community](https://discord.gg/serpex)
- 🐛 Issues: [GitHub Issues](https://github.com/divyeshradadiya/serpex-haystack/issues)
- 📖 Docs: [docs.serpex.dev](https://docs.serpex.dev)

## Acknowledgments

Built with ❤️ for the Haystack community by [Divyesh Radadiya](https://github.com/divyeshradadiya)

---

**Note**: This is a community-maintained integration. For Serpex API support, visit [serpex.dev](https://serpex.dev).
