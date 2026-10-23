"""
Tests for SerpexWebSearch component.

tests/fixtures holds sanitized responses captured from api.serpex.dev on 2026-10-23 (statuses that cannot be
triggered safely use the exact body from the backend code); manifest.json has each status and headers. The component
runs its real path through the official serpex SDK; only the SDK's HTTP session is replaced. No network.
"""

import copy
import json
import os
import pickle
import warnings
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest
from haystack.core.errors import ComponentError
from haystack.dataclasses import Document
from haystack.utils import Secret
from serpex import SerpApiException

from haystack_integrations.components.websearch import SerpexError as ExportedSerpexError
from haystack_integrations.components.websearch.serpex import USER_AGENT, SerpexError, SerpexWebSearch, _is_retryable

FIXTURES = Path(__file__).parent / "fixtures"
MANIFEST: Dict[str, Any] = json.loads((FIXTURES / "manifest.json").read_text())
IGNORED_PARAMS = ("engine", "engines", "category", "time_range", "num", "num_results")


def fixture(name: str) -> Any:
    return json.loads((FIXTURES / f"{name}.json").read_text())


class FakeResponse:
    def __init__(self, name: str) -> None:
        meta = MANIFEST[name]
        self.status_code = meta["status"]
        self.ok = 200 <= self.status_code < 300
        self.reason = ""
        self.headers = meta["headers"]
        self._body = fixture(name)

    def json(self) -> Any:
        return self._body


def serve(component: SerpexWebSearch, *names: str) -> List[Dict[str, Any]]:
    """Answer the component's requests with the given fixtures, in order (the last one repeats)."""
    sent: List[Dict[str, Any]] = []
    queue = list(names)
    client = component._get_client()

    def get(url: str, **kw: Any) -> FakeResponse:
        sent.append({"url": url, "query": {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}, **kw})
        return FakeResponse(queue.pop(0) if len(queue) > 1 else queue[0])

    client.session.get = get  # type: ignore[method-assign,assignment]
    component._make_request.retry.sleep = lambda _seconds: None  # type: ignore[attr-defined]  # no real backoff
    return sent


def make(**kw: Any) -> SerpexWebSearch:
    return SerpexWebSearch(api_key=Secret.from_token("test_key"), **kw)


class TestSerpexWebSearch:
    def test_init_default(self):
        with patch.dict(os.environ, {"SERPEX_API_KEY": "test_key"}):
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                component = SerpexWebSearch()
            assert component.engine is None
            assert component.timeout is None
            assert component.retry_attempts == 2
            assert component.include_content is False
            assert component.content_results == 5

    def test_init_custom(self):
        component = make(timeout=15.0, retry_attempts=3, include_content=True, content_results=10)
        assert component.timeout == 15.0
        assert component.retry_attempts == 3
        assert component.content_results == 10
        assert component._get_client().timeout == 15.0

    def test_init_deprecated_engine_warns(self):
        with pytest.warns(DeprecationWarning):
            make(engine="legacy-a")

    def test_content_results_must_be_5_or_10(self):
        with pytest.raises(ValueError):
            make(content_results=7)

    def test_to_dict(self):
        with patch.dict(os.environ, {"SERPEX_API_KEY": "test_key"}):
            component = SerpexWebSearch(api_key=Secret.from_env_var("SERPEX_API_KEY"), include_content=True)
            data = component.to_dict()
            assert data["type"] == "haystack_integrations.components.websearch.serpex.SerpexWebSearch"
            assert "engine" not in data["init_parameters"]
            assert data["init_parameters"]["include_content"] is True
            assert data["init_parameters"]["content_results"] == 5

    def test_from_dict_old_pipeline_with_engine(self):
        data = {
            "type": "haystack_integrations.components.websearch.serpex.SerpexWebSearch",
            "init_parameters": {
                "api_key": {"type": "env_var", "env_vars": ["SERPEX_API_KEY"], "strict": True},
                "engine": "auto",
                "timeout": 20.0,
                "retry_attempts": 4,
            },
        }
        with patch.dict(os.environ, {"SERPEX_API_KEY": "test_key"}):
            with warnings.catch_warnings():
                warnings.simplefilter("error")
                component = SerpexWebSearch.from_dict(data)
            assert component.engine is None
            assert component.timeout == 20.0
            assert component.retry_attempts == 4

    def test_retry_policy(self):
        """Only transport errors, 429 and 5xx are retried; 4xx never are"""
        for code in (400, 401, 402, 403, 404, 410):
            assert _is_retryable(SerpApiException("x", status_code=code)) is False
        for code in (429, 500, 502, 503, 504):
            assert _is_retryable(SerpApiException("x", status_code=code)) is True
        assert _is_retryable(SerpApiException("timeout")) is True
        assert _is_retryable(ValueError("x")) is False

    def test_run_success(self):
        component = make()
        sent = serve(component, "search_plain")
        docs = component.run(query="python asyncio tutorial")["documents"]
        assert sent[0]["url"].startswith("https://api.serpex.dev/api/search?")
        assert sent[0]["query"] == {"q": "python asyncio tutorial"}
        assert sent[0]["timeout"] >= 60
        assert len(docs) == 10
        first = fixture("search_plain")["results"][0]
        assert isinstance(docs[0], Document)
        assert docs[0].content == first["snippet"]
        assert docs[0].meta == {
            "title": first["title"],
            "url": first["url"],
            "position": 1,
            "query": "python asyncio tutorial",
            "engine": "auto",
        }

    def test_user_agent_names_sdk_and_component(self):
        ua = make()._get_client().session.headers["User-Agent"]
        assert USER_AGENT == "serpex-haystack/2.0.0"
        assert isinstance(ua, str) and ua.startswith("serpex-python/") and ua.endswith(" serpex-haystack/2.0.0")

    def test_run_sends_only_q(self):
        """Deprecated run() params are accepted, warned, and never sent"""
        component = make()
        sent = serve(component, "search_repeat_deprecated_engine")
        with pytest.warns(DeprecationWarning):
            component.run(query="python asyncio tutorial", engine="legacy-a", time_range="week")
        assert sent[0]["query"] == {"q": "python asyncio tutorial"}
        for name in IGNORED_PARAMS:
            assert name not in sent[0]["query"]

    def test_run_include_content(self):
        """include_content sends the content params and puts page markdown in Document.content"""
        component = make(include_content=True, content_results=5)
        sent = serve(component, "search_content")
        docs = component.run(query="what is retrieval augmented generation")["documents"]
        q = sent[0]["query"]
        assert q["include_content"].lower() == "true"
        assert q.get("content_results", "5") == "5"
        assert sent[0]["timeout"] >= 100
        raw = fixture("search_content")["results"]
        for i, doc in enumerate(docs):
            assert doc.meta["snippet"] == raw[i]["snippet"]
            if i < 5:
                assert doc.content == raw[i]["content"]
            else:
                assert doc.content == raw[i]["snippet"]
            assert "content_error" not in doc.meta

    def test_run_content_errors(self):
        component = make()
        serve(component, "search_content_errors")
        docs = component.run(query="x", include_content=True)["documents"]
        assert [d.meta.get("content_error") for d in docs[:5]] == ["robots_disallowed"] * 5
        assert all(d.content == d.meta["snippet"] for d in docs)

    def test_run_empty_results(self):
        component = make()
        serve(component, "search_no_results")
        assert component.run(query="x")["documents"] == []

    @pytest.mark.parametrize(
        "name,status,text",
        [
            (
                "error_400_content_results",
                400,
                "Serpex rejected the request (HTTP 400): content_results must be 5 or 10.",
            ),
            ("error_401_bad_key", 401, "Serpex rejected the API key (HTTP 401)"),
            ("error_402_search", 402, "Out of Serpex credits (HTTP 402)"),
        ],
    )
    def test_client_errors_are_not_retried(self, name, status, text):
        component = make(retry_attempts=3)
        sent = serve(component, name)
        with pytest.raises(SerpexError) as info:
            component.run(query="x")
        assert len(sent) == 1
        e = info.value
        assert isinstance(e, ComponentError) and e.status_code == status and e.retryable is False
        assert text in str(e)

    def test_rate_limit_and_5xx_are_retried(self):
        component = make(retry_attempts=3)
        sent = serve(component, "error_429", "error_503_search", "search_plain")
        docs = component.run(query="x")["documents"]
        assert len(sent) == 3 and len(docs) == 10

    def test_retries_exhausted_raise_a_clear_error(self):
        component = make(retry_attempts=2)
        sent = serve(component, "error_500_search")
        with pytest.raises(SerpexError) as info:
            component.run(query="x")
        assert len(sent) == 2
        assert info.value.retryable is True and info.value.status_code == 500
        assert (
            "Serpex is temporarily unavailable (HTTP 500): Internal server error. Not charged. Retry shortly."
            in str(info.value)
        )

    def test_error_is_exported(self):
        assert ExportedSerpexError is SerpexError

    def test_error_pickles_and_deep_copies(self):
        """Pipelines copy and pickle component errors (e.g. across processes); every field must survive."""
        component = make()
        serve(component, "error_402_search")
        with pytest.raises(SerpexError) as info:
            component.run(query="x")
        original = info.value
        for clone in (pickle.loads(pickle.dumps(original)), copy.deepcopy(original), copy.copy(original)):
            assert type(clone) is SerpexError and isinstance(clone, ComponentError)
            assert str(clone) == str(original)
            assert clone.status_code == 402 and clone.retryable is False
            assert clone.details == fixture("error_402_search")

    def test_error_defaults(self):
        e = SerpexError("boom")
        assert (e.status_code, e.details, e.retryable) == (None, {}, False)
        assert pickle.loads(pickle.dumps(e)).details == {}

    def test_cleanup(self):
        component = make()
        component._get_client()
        component.__del__()
