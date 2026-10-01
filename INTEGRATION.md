---
layout: integration
name: Serpex
description: Web search integration for Haystack, powered by Serpex
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

[Serpex](https://serpex.dev) is the web search API and extract API for AI agents. This Haystack integration enables you to seamlessly incorporate web search results into your RAG (Retrieval-Augmented Generation) pipelines and AI applications.

### Key Features

- 🔍 **Web Search**: One search engine, nothing to configure; optional page content as markdown
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

#### Page content

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

#### Deprecated parameters

Serpex is one search engine, so there is nothing to select. `engine` (in
`__init__` and `run()`) and `time_range` (in `run()`) are deprecated and ignored
by the Serpex API. They are still accepted so existing code keeps running, emit a
`DeprecationWarning`, and are not sent. Pipelines saved with an older version
still load: their `engine` value is dropped. Removed in 2.0.

#### Timeouts and retries

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

### Component API

#### SerpexWebSearch

**Parameters:**

- **api_key** (`Secret`, optional): Serpex API key. Defaults to `SERPEX_API_KEY` environment variable.
- **timeout** (`float`, optional): Request timeout in seconds. Defaults to 60, or 100 with `include_content`.
- **retry_attempts** (`int`, optional): Total attempts on a transport error, 429 or 5xx. Defaults to `2`.
- **include_content** (`bool`, optional): Also fetch page content (markdown) for the top results. Defaults to `False`.
- **content_results** (`int`, optional): How many top results get content, `5` or `10`. Defaults to `5`.
- **engine** (`str`, optional): **Deprecated** — ignored by the Serpex API and not sent.

**Inputs:**

- **query** (`str`): The search query string.
- **include_content** (`bool`, optional): Overrides the component setting for this call.
- **engine**, **time_range** (optional): **Deprecated** — ignored by the Serpex API and not sent.

**Outputs:**

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

### Error Handling

The component includes built-in retry logic with exponential backoff for handling transient errors:

```python
web_search = SerpexWebSearch(
    api_key=Secret.from_env_var("SERPEX_API_KEY"),
    timeout=90.0,        # Request timeout in seconds
    retry_attempts=3     # Total attempts on a transport error, 429 or 5xx
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
