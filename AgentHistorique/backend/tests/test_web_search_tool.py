from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx

from app.config import Settings
from app.tools.web_search_tool import (
    DuckDuckGoSearchTool,
    TavilySearchTool,
    WebSearchResult,
    create_web_search_tool,
)


def test_duckduckgo_search_maps_results() -> None:
    raw_results = [
        {
            "title": "Thermes d'Antonin",
            "href": "https://example.com/thermes",
            "body": "Complexe thermal romain à Carthage.",
        }
    ]
    tool = DuckDuckGoSearchTool()

    with patch("duckduckgo_search.DDGS") as mock_ddgs_cls:
        mock_ddgs = MagicMock()
        mock_ddgs.__enter__.return_value = mock_ddgs
        mock_ddgs.text.return_value = raw_results
        mock_ddgs_cls.return_value = mock_ddgs

        results = tool.search("Thermes d'Antonin Carthage", max_results=3)

    assert len(results) == 1
    assert results[0] == WebSearchResult(
        title="Thermes d'Antonin",
        url="https://example.com/thermes",
        snippet="Complexe thermal romain à Carthage.",
    )


def test_duckduckgo_search_returns_empty_on_failure() -> None:
    tool = DuckDuckGoSearchTool()

    with patch("duckduckgo_search.DDGS", side_effect=RuntimeError("network down")):
        results = tool.search("Carthage fouilles récentes")

    assert results == []


def test_duckduckgo_search_skips_empty_query() -> None:
    tool = DuckDuckGoSearchTool()
    assert tool.search("   ") == []


def test_tavily_search_maps_results() -> None:
    tool = TavilySearchTool(api_key="tvly-test")
    payload = {
        "results": [
            {
                "title": "Salammbô — Wikipédia",
                "url": "https://fr.wikipedia.org/wiki/Salammb%C3%B4",
                "content": "Roman historique de Gustave Flaubert sur Carthage.",
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = payload

    with patch("app.tools.web_search_tool.httpx.post", return_value=mock_response) as mock_post:
        results = tool.search("Salammbo Flaubert Carthage", max_results=3, region="fr-fr")

    assert len(results) == 1
    assert results[0] == WebSearchResult(
        title="Salammbô — Wikipédia",
        url="https://fr.wikipedia.org/wiki/Salammb%C3%B4",
        snippet="Roman historique de Gustave Flaubert sur Carthage.",
        source="tavily",
    )
    mock_post.assert_called_once()
    request_payload = mock_post.call_args.kwargs["json"]
    assert request_payload["api_key"] == "tvly-test"
    assert request_payload["query"] == "Salammbo Flaubert Carthage"
    assert request_payload["country"] == "france"
    assert request_payload["search_depth"] == "basic"


def test_tavily_search_returns_empty_on_failure() -> None:
    tool = TavilySearchTool(api_key="tvly-test")

    with patch(
        "app.tools.web_search_tool.httpx.post",
        side_effect=httpx.ConnectError("network down"),
    ):
        results = tool.search("Carthage fouilles récentes")

    assert results == []


def test_tavily_search_skips_empty_query_and_missing_api_key() -> None:
    tool = TavilySearchTool(api_key="")
    assert tool.search("   ") == []
    with patch("app.tools.web_search_tool.httpx.post") as mock_post:
        assert tool.search("Carthage") == []
    mock_post.assert_not_called()


def test_create_web_search_tool_selects_provider() -> None:
    duckduckgo_tool = create_web_search_tool(
        Settings(web_search_provider="duckduckgo", web_search_region="fr-fr")
    )
    assert isinstance(duckduckgo_tool, DuckDuckGoSearchTool)

    tavily_tool = create_web_search_tool(
        Settings(
            web_search_provider="tavily",
            tavily_api_key="tvly-test",
            web_search_region="fr-fr",
        )
    )
    assert isinstance(tavily_tool, TavilySearchTool)

    fallback_tool = create_web_search_tool(
        Settings(web_search_provider="tavily", tavily_api_key="")
    )
    assert isinstance(fallback_tool, DuckDuckGoSearchTool)
