# SPDX-FileCopyrightText: 2024-present Divyesh Radadiya <divyeshradadiya0@gmail.com>
#
# SPDX-License-Identifier: Apache-2.0

import re
import warnings
from typing import Any, Dict, List, Literal, Optional, cast

from haystack import component, default_from_dict, default_to_dict, logging
from haystack.core.errors import ComponentError
from haystack.dataclasses import Document
from haystack.utils import Secret, deserialize_secrets_inplace

# The official SDK owns the HTTP contract (params, timeouts, error parsing), so this component cannot drift from
# the API on its own.
from serpex import SearchParams, SearchResponse, SearchResult, SerpApiException, SerpexClient
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

__version__ = "2.0.0"

#: Product token appended to the SDK's User-Agent ("serpex-python/<sdk> serpex-haystack/<version>").
USER_AGENT = f"serpex-haystack/{__version__}"

BASE_URL = "https://api.serpex.dev"

BILLING_URL = "https://app.serpex.dev/dashboard/billing"


class SerpexError(ComponentError):
    """
    A Serpex request failed.

    :ivar status_code: HTTP status, or None for a timeout or a network failure.
    :ivar details: the parsed API error body, e.g. ``{"error": ..., "retryAfterMs": 292, "limit": 5}``.
    :ivar retryable: True when the same request can succeed on retry (429, 5xx, timeout, network).
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        retryable: bool = False,
    ) -> None:
        # Defaults matter: pickle and copy.deepcopy rebuild an exception as
        # cls(*args) with args == (message,), then restore __dict__.
        super().__init__(message)
        self.status_code = status_code
        self.details: Dict[str, Any] = dict(details or {})
        self.retryable = retryable


def _is_retryable(error: BaseException) -> bool:
    """Retry transport errors, 429 and 5xx only. 4xx (bad request, auth, credits, plan) never succeed on retry."""
    if isinstance(error, SerpApiException):
        status = error.status_code
        return status is None or status == 429 or status >= 500
    return False


def _sentence(text: str) -> str:
    return text if re.search(r"[.!?]$", text) else f"{text}."


def _api_message(err: SerpApiException) -> str:
    """The API's own error text (string, ``{"message"}`` or framework ``message``)."""
    details = err.details or {}
    error = details.get("error")
    if isinstance(error, str) and error:
        message = details.get("message")
        if err.status_code == 404 and isinstance(message, str) and message:
            return message
        return error
    if isinstance(error, dict) and isinstance(error.get("message"), str) and error["message"]:
        return str(error["message"])
    if isinstance(details.get("message"), str) and details["message"]:
        return str(details["message"])
    return str(err.args[0]) if err.args else "API request failed"


def describe_serpex_error(err: SerpApiException) -> str:
    """One actionable sentence per failure: what happened, whether it was charged, whether to retry."""
    status = err.status_code
    details = err.details or {}
    msg = _api_message(err)
    if status is None:
        return f"Serpex request failed: {_sentence(msg)} Safe to retry."
    if status == 400:
        return f"Serpex rejected the request (HTTP 400): {_sentence(msg)}"
    if status == 401:
        return f"Serpex rejected the API key (HTTP 401): {_sentence(msg)} Check SERPEX_API_KEY."
    if status == 402:
        balance = details.get("remainingCredits")
        balance_text = f" Balance: {balance} credits." if isinstance(balance, int) else ""
        return f"Out of Serpex credits (HTTP 402).{balance_text} Top up at {BILLING_URL}."
    if status == 429:
        limit = details.get("limit")
        limit_text = f" (limit: {limit} requests per second)" if isinstance(limit, int) else ""
        wait = details.get("retryAfterMs")
        wait_ms = wait if isinstance(wait, int) else 1000
        return f"Serpex rate limit exceeded{limit_text}. Retry in {wait_ms} ms."
    if status >= 500:
        charged = "" if re.search("charged", msg, re.I) else " Not charged."
        retry_hint = "" if re.search("retry", msg, re.I) else " Retry shortly."
        return f"Serpex is temporarily unavailable (HTTP {status}): {_sentence(msg)}{charged}{retry_hint}"
    return f"Serpex request failed (HTTP {status}): {_sentence(msg)}"


def _warn_deprecated(names: List[str]) -> None:
    warnings.warn(
        f"SerpexWebSearch: {', '.join(names)} {'is' if len(names) == 1 else 'are'} deprecated and ignored by the "
        "Serpex API; the value is not sent. It will be removed in 3.0.",
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

    A failed request raises `SerpexError` (a Haystack `ComponentError`) with the HTTP status, the API's message,
    whether it was charged and whether to retry.
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
                      working (emits a DeprecationWarning); removed in 3.0.
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
        self._client: Optional[SerpexClient] = None

        @retry(
            reraise=True,
            stop=stop_after_attempt(self.retry_attempts),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception(_is_retryable),
        )
        def make_request(params: SearchParams) -> SearchResponse:
            return self._get_client().search(params)

        self._make_request = make_request

    def _get_client(self) -> SerpexClient:
        """The SDK client, created on first use (the API key is resolved then, not at init)."""
        if self._client is None:
            client = SerpexClient(self.api_key.resolve_value() or "", base_url=BASE_URL, timeout=self.timeout)
            base_ua = client.session.headers.get("User-Agent", "")
            if isinstance(base_ua, bytes):
                base_ua = base_ua.decode("ascii", "replace")
            client.session.headers["User-Agent"] = f"{base_ua} {USER_AGENT}".strip()
            self._client = client
        return self._client

    def __del__(self):
        """
        Clean up resources when the component is deleted.

        Closes the HTTP session to prevent resource leaks.
        """
        try:
            if getattr(self, "_client", None) is not None:
                self._client.session.close()  # type: ignore[union-attr]
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

    def _build_params(self, query: str, with_content: bool) -> SearchParams:
        """Only q, include_content and content_results reach the API."""
        if with_content:
            return SearchParams(q=query, include_content=True, content_results=cast(Any, self.content_results))
        return SearchParams(q=query)

    @staticmethod
    def _to_document(result: SearchResult, query: str, with_content: bool) -> Document:
        """Map one API result to a Document: page content when extracted, otherwise the snippet."""
        meta: Dict[str, Any] = {
            "title": result.title,
            "url": result.url,
            "position": result.position,
            "query": query,
            # Deprecated: always "auto"; removed in 3.0.
            "engine": "auto",
        }
        if with_content:
            meta["snippet"] = result.snippet
            if result.content_error is not None:
                meta["content_error"] = result.content_error
        return Document(content=result.content if result.content is not None else result.snippet, meta=meta)

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

        :param query: The search query string. Operators such as `site:`, `-site:`, `after:YYYY-MM-DD` and
            `before:YYYY-MM-DD` go here.
        :param engine: Deprecated — ignored by the Serpex API and not sent; removed in 3.0.
        :param time_range: Deprecated — ignored by the Serpex API and not sent; removed in 3.0. Put
            `after:YYYY-MM-DD` in the query instead.
        :param include_content: Overrides the component's include_content for this call.
        :returns: Dictionary containing a list of Document objects with search results.
        :raises SerpexError: When the request fails (after retries for 429, 5xx and transport errors).
        """
        passed = [name for name, value in (("engine", engine), ("time_range", time_range)) if value is not None]
        if passed:
            _warn_deprecated(passed)

        with_content = self.include_content if include_content is None else include_content

        try:
            response = self._make_request(self._build_params(query, with_content))
        except SerpApiException as e:
            message = describe_serpex_error(e)
            # Not `message=`: that key collides with logging.LogRecord.message.
            logger.error("Serpex search failed: {reason}", reason=message)
            raise SerpexError(message, e.status_code, dict(e.details or {}), _is_retryable(e)) from e

        documents = [self._to_document(result, query, with_content) for result in response.results]
        if documents:
            logger.info(
                "Successfully fetched {count} search results for query: {query}",
                count=len(documents),
                query=query,
            )
        else:
            logger.warning(
                "No results found in Serpex API response for query: {query} ({reason})",
                query=query,
                reason=response.message or response.metadata.message or "",
            )

        return {"documents": documents}
