"""
Basic example of using SerpexWebSearch component
"""


from haystack.utils import Secret

from haystack_integrations.components.websearch.serpex import SerpexWebSearch


def main():
    # Initialize the component
    web_search = SerpexWebSearch(
        api_key=Secret.from_env_var("SERPEX_API_KEY"),
        engine="google",
    )

    # Perform a search
    query = "What is Haystack AI framework?"
    print(f"Searching for: {query}\n")

    results = web_search.run(query=query)

    # Display results
    print(f"Found {len(results['documents'])} results:\n")
    for i, doc in enumerate(results["documents"], 1):
        print(f"{i}. {doc.meta['title']}")
        print(f"   URL: {doc.meta['url']}")
        print(f"   Snippet: {doc.content}")
        print()


if __name__ == "__main__":
    main()
