# SPDX-FileCopyrightText: 2024-present Divyesh Radadiya <divyeshradadiya0@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

import warnings
from typing import Any, Dict, List, Literal, Optional, cast

import httpx
from haystack import component, default_from_dict, default_to_dict, logging
from haystack.dataclasses import Document
from haystack.utils import Secret, deserialize_secrets_inplace
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

__version__ = "1.1.0"

USER_AGENT = f"serpex-haystack/{__version__}"

# Client timeouts (seconds), above the server's own budget for each call (search 30 s upstream,
# 45 s with include_content), so a slow search is not abandoned client-side after the server
# has already finished and billed it.
SEARCH_TIMEOUT = 60.0
SEARCH_CONTENT_TIMEOUT = 100.0


def _is_retryable(error: BaseException) -> bool:
    """Retry transport errors, 429 and 5xx only. 4xx (bad request, auth, credits, plan) never succeed on retry."""
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        return status == 429 or status >= 500
    return isinstance(error, httpx.RequestError)


def _warn_deprecated(names: List[str]) -> None:
    warnings.warn(
        f"SerpexWebSearch: {', '.join(names)} {'is' if len(names) == 1 else 'are'} deprecated and ignored by the "
        "Serpex API; the value is not sent. It will be removed in 2.0.",
        DeprecationWarning,
        stacklevel=3,
    )


@component
class SerpexWebSearch:
    """
    Fetches web search results from the Serpex API.

    Serpex is the web search API and extract API for AI agents.
    Use it to retrieve ranked web results, snippets and, optionally, page content as markdown.

    ### Usage example

    ```python
    from haystack_integrations.components.websearch.serpex import SerpexWebSearch
    from haystack.utils import Secret

    fetcher = SerpexWebSearch(api_key=Secret.from_token("your-serpex-api-key"))
    results = fetcher.run(query="What is Haystack?")

    documents = results["documents"]
    for doc in documents:
        print(f"Title: {doc.meta['title']}")
        print(f"URL: {doc.meta['url']}")
        print(f"Snippet: {doc.content}")
    ```
    """

    def __init__(
        self,
        *,
        api_key: Secret = Secret.from_env_var("SERPEX_API_KEY"),
        engine: Optional[str] = None,
        timeout: Optional[float] = None,
        retry_attempts: int = 2,
        include_content: bool = False,
        content_results: int = 5,
    ) -> None:
        """
        Initializes the SerpexWebSearch component.

        :param api_key: Serpex API key for authentication. Get yours at https://serpex.dev
        :param engine: Deprecated — ignored by the Serpex API and not sent. Still accepted so existing code keeps
                      working (emits a DeprecationWarning); removed in 2.0.
        :param timeout: Timeout in seconds for the API request. Defaults to 60, or 100 with include_content.
        :param retry_attempts: Total attempts for a request that fails with a transport error, 429 or 5xx.
                              4xx errors are never retried. Defaults to 2.
        :param include_content: Also fetch page content (markdown) for the top results; each Document then carries
                               the page content in `content` and the snippet in `meta["snippet"]`. Defaults to False.
        :param content_results: How many top results get content when include_content is on: 5 or 10. Defaults to 5.
        """
        if engine is not None:
            _warn_deprecated(["engine"])
        if content_results not in (5, 10):
            raise ValueError("content_results must be 5 or 10")

        self.api_key = api_key
        self.engine = engine
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.include_content = include_content
        self.content_results = content_results

        # Create httpx client
        self._client = httpx.Client(follow_redirects=True, headers={"User-Agent": USER_AGENT})

        # Define retry decorator
        @retry(
            reraise=True,
            stop=stop_after_attempt(self.retry_attempts),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception(_is_retryable),
        )
        def make_request(url: str, headers: Dict[str, str], params: Dict[str, Any], timeout: float) -> httpx.Response:
            response = self._client.get(url, headers=headers, params=params, timeout=timeout)
            response.raise_for_status()
            return response

        self._make_request = make_request

    def __del__(self):
        """
        Clean up resources when the component is deleted.

        Closes the HTTP client to prevent resource leaks.
        """
        try:
            if hasattr(self, "_client"):
                self._client.close()
        except Exception:
            pass

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the component to a dictionary.

        The deprecated `engine` is not serialized.

        :returns: Dictionary with serialized data.
        """
        return cast(
            Dict[str, Any],
            default_to_dict(
                self,
                api_key=self.api_key.to_dict(),
                timeout=self.timeout,
                retry_attempts=self.retry_attempts,
                include_content=self.include_content,
                content_results=self.content_results,
            ),
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SerpexWebSearch":
        """
        Deserializes the component from a dictionary.

        Pipelines saved with an earlier version carry `engine`; it is dropped silently here (it was never the
        pipeline author's choice to keep it).

        :param data: Dictionary to deserialize from.
        :returns: Deserialized component.
        """
        data["init_parameters"].pop("engine", None)
        deserialize_secrets_inplace(data["init_parameters"], keys=["api_key"])
        return cast("SerpexWebSearch", default_from_dict(cls, data))

    def _build_params(self, query: str, with_content: bool) -> Dict[str, Any]:
        """Only q, include_content and content_results reach the API."""
        params: Dict[str, Any] = {"q": query}
        if with_content:
            params["include_content"] = "true"
            params["content_results"] = self.content_results
        return params

    def _request_timeout(self, with_content: bool) -> float:
        if self.timeout is not None:
            return self.timeout
        return SEARCH_CONTENT_TIMEOUT if with_content else SEARCH_TIMEOUT

    @staticmethod
    def _to_document(result: Dict[str, Any], query: str, with_content: bool) -> Document:
        """Map one API result to a Document: page content when extracted, otherwise the snippet."""
        snippet = result.get("snippet", "")
        meta: Dict[str, Any] = {
            "title": result.get("title", ""),
            "url": result.get("url", ""),
            "position": result.get("position", 0),
            "query": query,
            # Deprecated: always "auto"; removed in 2.0.
            "engine": "auto",
        }
        if with_content:
            meta["snippet"] = snippet
            if result.get("content_error"):
                meta["content_error"] = result["content_error"]
        return Document(content=result.get("content") or snippet, meta=meta)

    @component.output_types(documents=List[Document])
    def run(
        self,
        query: str,
        *,
        engine: Optional[str] = None,
        time_range: Optional[Literal["all", "day", "week", "month", "year"]] = None,
        include_content: Optional[bool] = None,
    ) -> Dict[str, List[Document]]:
        """
        Fetches web search results for the given query.

        :param query: The search query string.
        :param engine: Deprecated — ignored by the Serpex API and not sent; removed in 2.0.
        :param time_range: Deprecated — ignored by the Serpex API and not sent; removed in 2.0.
        :param include_content: Overrides the component's include_content for this call.
        :returns: Dictionary containing a list of Document objects with search results.
        """
        documents: List[Document] = []

        passed = [name for name, value in (("engine", engine), ("time_range", time_range)) if value is not None]
        if passed:
            _warn_deprecated(passed)

        with_content = self.include_content if include_content is None else include_content

        try:
            params = self._build_params(query, with_content)
            timeout = self._request_timeout(with_content)
            headers = {
                "Authorization": f"Bearer {self.api_key.resolve_value()}",
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            }

            # Make API request
            response = self._make_request("https://api.serpex.dev/api/search", headers, params, timeout)
            data = response.json()

            # Parse search results
            if "results" in data and isinstance(data["results"], list):
                documents = [self._to_document(result, query, with_content) for result in data["results"]]

                logger.info(
                    "Successfully fetched {count} search results for query: {query}",
                    count=len(documents),
                    query=query,
                )
            else:
                logger.warning(
                    "No results found in Serpex API response for query: {query}",
                    query=query,
                )

        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error occurred while fetching Serpex results: {status} - {detail}",
                status=e.response.status_code,
                detail=str(e),
            )
            raise
        except httpx.RequestError as e:
            logger.error("Request error occurred while fetching Serpex results: {error}", error=e)
            raise
        except Exception as e:
            logger.error(
                "Unexpected error occurred while fetching Serpex results: {error}",
                error=e,
            )
            raise

        return {"documents": documents}
