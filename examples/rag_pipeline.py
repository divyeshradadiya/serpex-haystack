"""
Example of building a RAG pipeline with web search
"""

from haystack import Pipeline
from haystack.components.builders import PromptBuilder
from haystack.components.generators import OpenAIGenerator
from haystack.utils import Secret
from haystack_integrations.components.websearch.serpex import SerpexWebSearch


def main():
    # Define the prompt template
    prompt_template = """
Based on the following web search results, provide a comprehensive answer to the question.

Search Results:
{% for doc in documents %}
{{ loop.index }}. {{ doc.meta.title }}
   {{ doc.content }}
   Source: {{ doc.meta.url }}

{% endfor %}

Question: {{ query }}

Provide a detailed answer based on the search results above. Include relevant sources in your answer.

Answer:
"""

    # Build the pipeline
    pipe = Pipeline()

    # Add components
    pipe.add_component("search", SerpexWebSearch(api_key=Secret.from_env_var("SERPEX_API_KEY"), num_results=5))
    pipe.add_component("prompt", PromptBuilder(template=prompt_template))
    pipe.add_component("llm", OpenAIGenerator(api_key=Secret.from_env_var("OPENAI_API_KEY"), model="gpt-4"))

    # Connect components
    pipe.connect("search.documents", "prompt.documents")
    pipe.connect("prompt", "llm")

    # Run the pipeline
    query = "What are the latest developments in AI agents?"
    print(f"Question: {query}\n")
    print("Searching and generating answer...\n")

    result = pipe.run({"search": {"query": query}, "prompt": {"query": query}})

    # Display the answer
    print("Answer:")
    print("-" * 80)
    print(result["llm"]["replies"][0])
    print("-" * 80)


if __name__ == "__main__":
    main()
