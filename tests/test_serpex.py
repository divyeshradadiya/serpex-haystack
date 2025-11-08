"""
Tests for SerpexWebSearch component
"""

import os
from unittest.mock import Mock, patch

from haystack.dataclasses import Document
from haystack.utils import Secret

from haystack_integrations.components.websearch.serpex import SerpexWebSearch


class TestSerpexWebSearch:
    def test_init_default(self):
        """Test initialization with default parameters"""
        with patch.dict(os.environ, {"SERPEX_API_KEY": "test_key"}):
            component = SerpexWebSearch()
            assert component.engine == "google"
            assert component.timeout == 10.0
            assert component.retry_attempts == 2

    def test_init_custom(self):
        """Test initialization with custom parameters"""
        component = SerpexWebSearch(
            api_key=Secret.from_token("custom_key"),
            engine="bing",
            timeout=15.0,
            retry_attempts=3,
        )
        assert component.engine == "bing"
        assert component.timeout == 15.0
        assert component.retry_attempts == 3

    def test_to_dict(self):
        """Test serialization to dictionary"""
        with patch.dict(os.environ, {"SERPEX_API_KEY": "test_key"}):
            component = SerpexWebSearch(
                api_key=Secret.from_env_var("SERPEX_API_KEY"),
                engine="duckduckgo",
            )
            data = component.to_dict()

            assert data["type"] == "haystack_integrations.components.websearch.serpex.SerpexWebSearch"
            assert data["init_parameters"]["engine"] == "duckduckgo"

    def test_from_dict(self):
        """Test deserialization from dictionary"""
        data = {
            "type": "haystack_integrations.components.websearch.serpex.SerpexWebSearch",
            "init_parameters": {
                "api_key": {"type": "env_var", "env_vars": ["SERPEX_API_KEY"], "strict": True},
                "engine": "brave",
                "timeout": 20.0,
                "retry_attempts": 4,
            },
        }

        with patch.dict(os.environ, {"SERPEX_API_KEY": "test_key"}):
            component = SerpexWebSearch.from_dict(data)
            assert component.engine == "brave"
            assert component.timeout == 20.0
            assert component.retry_attempts == 4

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
    def test_run_with_overrides(self, mock_client):
        """Test search with runtime parameter overrides"""
        mock_response = Mock()
        mock_response.json.return_value = {"results": []}

        mock_instance = Mock()
        mock_instance.get.return_value = mock_response
        mock_client.return_value = mock_instance

        component = SerpexWebSearch(api_key=Secret.from_token("test_key"))
        component.run(query="test", engine="bing", time_range="week")

        # Check that parameters were passed correctly
        call_args = mock_instance.get.call_args
        params = call_args[1]["params"]
        assert params["engine"] == "bing"
        assert params["time_range"] == "week"

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
