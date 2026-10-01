"""
Tests for SerpexWebSearch component
"""

import os
import warnings
from unittest.mock import Mock, patch

import httpx
import pytest
from haystack.dataclasses import Document
from haystack.utils import Secret

from haystack_integrations.components.websearch.serpex import USER_AGENT, SerpexWebSearch, _is_retryable

IGNORED_PARAMS = ("engine", "engines", "category", "time_range", "num")


class TestSerpexWebSearch:
    def test_init_default(self):
        """Test initialization with default parameters"""
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
        """Test initialization with custom parameters"""
        component = SerpexWebSearch(
            api_key=Secret.from_token("custom_key"),
            timeout=15.0,
            retry_attempts=3,
            include_content=True,
            content_results=10,
        )
        assert component.timeout == 15.0
        assert component.retry_attempts == 3
        assert component.content_results == 10

    def test_init_deprecated_engine_warns(self):
        with pytest.warns(DeprecationWarning):
            SerpexWebSearch(api_key=Secret.from_token("custom_key"), engine="legacy-a")

    def test_content_results_must_be_5_or_10(self):
        with pytest.raises(ValueError):
            SerpexWebSearch(api_key=Secret.from_token("custom_key"), content_results=7)

    def test_to_dict(self):
        """Test serialization to dictionary: the deprecated engine is not written"""
        with patch.dict(os.environ, {"SERPEX_API_KEY": "test_key"}):
            component = SerpexWebSearch(api_key=Secret.from_env_var("SERPEX_API_KEY"), include_content=True)
            data = component.to_dict()

            assert data["type"] == "haystack_integrations.components.websearch.serpex.SerpexWebSearch"
            assert "engine" not in data["init_parameters"]
            assert data["init_parameters"]["include_content"] is True
            assert data["init_parameters"]["content_results"] == 5

    def test_from_dict_old_pipeline_with_engine(self):
        """A pipeline saved by 1.0.x (with engine) still loads, silently dropping engine"""
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
        request = httpx.Request("GET", "https://api.serpex.dev/api/search")

        def status_error(code):
            return httpx.HTTPStatusError("x", request=request, response=httpx.Response(code, request=request))

        for code in (400, 401, 402, 403, 404):
            assert _is_retryable(status_error(code)) is False
        for code in (429, 500, 503):
            assert _is_retryable(status_error(code)) is True
        assert _is_retryable(httpx.ConnectError("x", request=request)) is True
        assert _is_retryable(ValueError("x")) is False

    @patch("haystack_integrations.components.websearch.serpex.httpx.Client")
    def test_run_success(self, mock_client):
        """Test successful search"""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Test Title 1",
                    "url": "https://example.com/1",
                    "snippet": "Test snippet 1",
                    "position": 1,
                },
                {
                    "title": "Test Title 2",
                    "url": "https://example.com/2",
                    "snippet": "Test snippet 2",
                    "position": 2,
                },
            ]
        }

        # Setup mock client
        mock_instance = Mock()
        mock_instance.get.return_value = mock_response
        mock_client.return_value = mock_instance

        component = SerpexWebSearch(api_key=Secret.from_token("test_key"))
        result = component.run(query="test query")

        assert "documents" in result
        assert len(result["documents"]) == 2

        doc1 = result["documents"][0]
        assert isinstance(doc1, Document)
        assert doc1.content == "Test snippet 1"
        assert doc1.meta["title"] == "Test Title 1"
        assert doc1.meta["url"] == "https://example.com/1"
        assert doc1.meta["position"] == 1
        assert doc1.meta["query"] == "test query"

    @patch("haystack_integrations.components.websearch.serpex.httpx.Client")
    def test_run_sends_only_q(self, mock_client):
        """Deprecated run() params are accepted, warned, and never sent"""
        mock_response = Mock()
        mock_response.json.return_value = {"results": []}

        mock_instance = Mock()
        mock_instance.get.return_value = mock_response
        mock_client.return_value = mock_instance

        component = SerpexWebSearch(api_key=Secret.from_token("test_key"))
        with pytest.warns(DeprecationWarning):
            component.run(query="test", engine="legacy-a", time_range="week")

        call_kwargs = mock_instance.get.call_args[1]
        assert call_kwargs["params"] == {"q": "test"}
        for name in IGNORED_PARAMS:
            assert name not in call_kwargs["params"]
        assert call_kwargs["headers"]["User-Agent"] == USER_AGENT == "serpex-haystack/1.1.0"
        assert call_kwargs["timeout"] >= 30

    @patch("haystack_integrations.components.websearch.serpex.httpx.Client")
    def test_run_include_content(self, mock_client):
        """include_content sends the content params and puts page markdown in Document.content"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {"title": "A", "url": "https://a.example", "snippet": "snip A", "position": 1, "content": "# Page A"},
                {
                    "title": "B",
                    "url": "https://b.example",
                    "snippet": "snip B",
                    "position": 2,
                    "content_error": "timeout",
                },
            ]
        }

        mock_instance = Mock()
        mock_instance.get.return_value = mock_response
        mock_client.return_value = mock_instance

        component = SerpexWebSearch(api_key=Secret.from_token("test_key"), include_content=True, content_results=10)
        docs = component.run(query="test")["documents"]

        call_kwargs = mock_instance.get.call_args[1]
        assert call_kwargs["params"] == {"q": "test", "include_content": "true", "content_results": 10}
        assert call_kwargs["timeout"] >= 60
        assert docs[0].content == "# Page A"
        assert docs[0].meta["snippet"] == "snip A"
        assert docs[1].content == "snip B"
        assert docs[1].meta["content_error"] == "timeout"

    @patch("haystack_integrations.components.websearch.serpex.httpx.Client")
    def test_run_empty_results(self, mock_client):
        """Test handling of empty results"""
        mock_response = Mock()
        mock_response.json.return_value = {"results": []}

        mock_instance = Mock()
        mock_instance.get.return_value = mock_response
        mock_client.return_value = mock_instance

        component = SerpexWebSearch(api_key=Secret.from_token("test_key"))
        result = component.run(query="test query")

        assert "documents" in result
        assert len(result["documents"]) == 0

    def test_cleanup(self):
        """Test resource cleanup"""
        component = SerpexWebSearch(api_key=Secret.from_token("test_key"))
        assert hasattr(component, "_client")

        # Trigger cleanup
        component.__del__()
        # Should not raise any exceptions
