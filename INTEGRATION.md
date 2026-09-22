---
layout: integration
name: Serpex
description: Real-time web search integration for Haystack, powered by Serpex
authors:
    - name: Divyesh Radadiya
      socials:
        github: divyeshradadiya
pypi: https://pypi.org/project/serpex-haystack/
repo: https://github.com/divyeshradadiya/serpex-haystack
type: Custom Component
report_issue: https://github.com/divyeshradadiya/serpex-haystack/issues
logo: /logos/serpex.png
version: Haystack 2.0
toc: true
---

### **Table of Contents**
- [Overview](#overview)
- [Installation](#installation)
- [Usage](#usage)
- [License](#license)

## Overview

[Serpex](https://serpex.dev) is a real-time web search API. This Haystack integration enables you to seamlessly incorporate web search results into your RAG (Retrieval-Augmented Generation) pipelines and AI applications.

### Key Features

- 🔍 **Real-Time Web Search**: One search engine, nothing to configure
- ⚡ **High Performance**: Fast and reliable with automatic retry logic and exponential backoff
- 🎯 **Rich Results**: Get organic search results with titles, snippets, URLs, and positions
- 🕒 **Time Filters**: Filter results by day, week, month, or year
- 🔒 **Type-Safe**: Fully typed with comprehensive type hints
- 📝 **Haystack Native**: Seamless integration with Haystack 2.0+ components

## Installation

```bash
pip install serpex-haystack
```

To use this integration, you'll need a Serpex API key. Sign up at [serpex.dev](https://serpex.dev) to get your API key.

## Usage

### Basic Usage

```python
from haystack.utils import Secret
from haystack_integrations.components.websearch.serpex import SerpexWebSearch

# Initialize the component
web_search = SerpexWebSearch(
    api_key=Secret.from_env_var("SERPEX_API_KEY"),
)

# Perform a search
results = web_search.run(query="What is Haystack AI?")

# Access the results
for doc in results["documents"]:
    print(f"Title: {doc.meta['title']}")
    print(f"URL: {doc.meta['url']}")
    print(f"Snippet: {doc.content}\n")
```

### RAG Pipeline Example

Build a complete RAG pipeline with web search:

```python
from haystack import Pipeline
from haystack.components.builders import PromptBuilder
from haystack.components.generators import OpenAIGenerator
from haystack.utils import Secret
from haystack_integrations.components.websearch.serpex import SerpexWebSearch

# Define prompt template
prompt_template = """
Based on the following search results, answer the question comprehensively.

Search Results:
{% for doc in documents %}
{{ loop.index }}. {{ doc.meta.title }}
   {{ doc.content }}
   Source: {{ doc.meta.url }}

{% endfor %}

Question: {{ query }}

Answer:
"""

# Build the pipeline
pipe = Pipeline()
pipe.add_component("search", SerpexWebSearch(
    api_key=Secret.from_env_var("SERPEX_API_KEY"),
))
pipe.add_component("prompt", PromptBuilder(template=prompt_template))
pipe.add_component("llm", OpenAIGenerator(
    api_key=Secret.from_env_var("OPENAI_API_KEY")
))

# Connect components
pipe.connect("search.documents", "prompt.documents")
pipe.connect("prompt", "llm")

# Run the pipeline
result = pipe.run({
    "search": {"query": "Latest developments in AI agents"},
    "prompt": {"query": "Latest developments in AI agents"}
})

print(result["llm"]["replies"][0])
```

### Advanced Features

#### The `engine` parameter (deprecated)

Serpex is one search engine, so there is nothing to select. `engine` is
deprecated and ignored by the Serpex API since 2026-06; it is still accepted so
existing pipelines keep working, and defaults to `"auto"`.

#### Time Range Filtering

```python
# Get only recent results
recent_results = web_search.run(
    query="AI news",
    time_range="week"  # Options: day, week, month, year, all
)
```

#### Runtime Parameter Override

```python
# Override default settings per query
results = web_search.run(
    query="Python tutorials",
    time_range="month",
)
```

### Component API

#### SerpexWebSearch

**Parameters:**
- `api_key` (Secret): Serpex API key. Defaults to `SERPEX_API_KEY` environment variable.
- `engine` (str): **Deprecated** — ignored by the Serpex API. Still accepted; default: "auto".
- `timeout` (float): Request timeout in seconds. Default: 10.0.
- `retry_attempts` (int): Number of retry attempts for failed requests. Default: 2.

**Inputs:**
- `query` (str): The search query string.
- `engine` (str, optional): **Deprecated** — still accepted, ignored by the API.
- `time_range` (str, optional): Filter by time range ("all", "day", "week", "month", "year").

**Outputs:**
- `documents` (List[Document]): List of Haystack Document objects with search results.

Each document contains:
- `content`: The search result snippet
- `meta`:
  - `title`: Result title
  - `url`: Result URL
  - `position`: Position in search results
  - `query`: Original search query
  - `engine`: Legacy field, kept for compatibility

### Error Handling

The component includes built-in retry logic with exponential backoff for handling transient errors:

```python
web_search = SerpexWebSearch(
    api_key=Secret.from_env_var("SERPEX_API_KEY"),
    timeout=15.0,        # Increase timeout for slower networks
    retry_attempts=3     # Retry up to 3 times on failure
)
```

## License

`serpex-haystack` is distributed under the terms of the [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) license.

---

**Additional Resources:**
- [Serpex API Documentation](https://docs.serpex.dev)
- [GitHub Repository](https://github.com/divyeshradadiya/serpex-haystack)
- [Report Issues](https://github.com/divyeshradadiya/serpex-haystack/issues)
- [PyPI Package](https://pypi.org/project/serpex-haystack/)

**Support:**
- Email: support@serpex.dev
- Discord: [Join our community](https://discord.gg/serpex)
