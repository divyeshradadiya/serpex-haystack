"""
Example of using web search with a Haystack agent
"""

from haystack import Pipeline
from haystack.components.builders import PromptBuilder
from haystack.components.generators import OpenAIGenerator
from haystack.utils import Secret
from haystack_integrations.components.websearch.serpex import SerpexWebSearch


def create_research_agent():
    """Create an agent that can search the web and answer questions"""

    # Template for the agent
    agent_template = """
You are a helpful research assistant with access to web search.

Your task is to answer the user's question using the provided search results.
Be accurate, cite sources, and if the search results don't contain enough information, say so.

Search Results:
{% for doc in documents %}
- {{ doc.meta.title }}: {{ doc.content }}
  (Source: {{ doc.meta.url }})
{% endfor %}

User Question: {{ query }}

Your Answer:
"""

    # Build the agent pipeline
    agent = Pipeline()
    agent.add_component("search", SerpexWebSearch(api_key=Secret.from_env_var("SERPEX_API_KEY"), num_results=8))
    agent.add_component("prompt", PromptBuilder(template=agent_template))
    agent.add_component("llm", OpenAIGenerator(api_key=Secret.from_env_var("OPENAI_API_KEY"), model="gpt-4"))

    agent.connect("search.documents", "prompt.documents")
    agent.connect("prompt", "llm")

    return agent


def main():
    # Create the agent
    agent = create_research_agent()

    # Example questions
    questions = [
        "What are the main features of Haystack 2.0?",
        "How does retrieval-augmented generation work?",
        "What are the best practices for building LLM applications?",
    ]

    print("Research Agent with Web Search")
    print("=" * 80)

    for question in questions:
        print(f"\nQ: {question}")
        print("-" * 80)

        result = agent.run({"search": {"query": question}, "prompt": {"query": question}})

        print(f"A: {result['llm']['replies'][0]}")
        print()


if __name__ == "__main__":
    main()
