"""
Example comparing results from different search engines
"""

from haystack.utils import Secret

from haystack_integrations.components.websearch.serpex import SerpexWebSearch


def main():
    query = "Python web scraping best practices"
    engines = ["google", "bing", "duckduckgo"]

    print(f"Comparing search results for: '{query}'\n")
    print("=" * 100)

    for engine in engines:
        print(f"\n{engine.upper()} Results:")
        print("-" * 100)

        search = SerpexWebSearch(api_key=Secret.from_env_var("SERPEX_API_KEY"), engine=engine)

        results = search.run(query=query)

        for i, doc in enumerate(results["documents"], 1):
            print(f"\n{i}. {doc.meta['title']}")
            print(f"   {doc.content[:150]}...")
            print(f"   {doc.meta['url']}")

        print()


if __name__ == "__main__":
    main()
