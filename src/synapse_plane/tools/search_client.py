"""Tavily web search — used by Open Deep Research and the Tavily-backed
Browser Use venue-discovery adapter (see docs decision: search-based, not
live browser automation)."""

from typing import Protocol

import httpx

from synapse_plane.domain.tools import WebSearchResult

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


class SearchClientProtocol(Protocol):
    async def search(self, query: str, max_results: int = 5) -> list[WebSearchResult]: ...


# Real Tavily-backed search
class TavilySearchClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def search(self, query: str, max_results: int = 5) -> list[WebSearchResult]:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                TAVILY_SEARCH_URL,
                json={"api_key": self.api_key, "query": query, "max_results": max_results},
            )
            response.raise_for_status()
            data = response.json()
        return [
            WebSearchResult(
                title=r.get("title", ""), url=r.get("url", ""), content=r.get("content", "")
            )
            for r in data.get("results", [])
        ]


# Deterministic canned results — no network calls. Used in all tests.
class FakeSearchClient:
    def __init__(self, canned: dict[str, list[WebSearchResult]] | None = None):
        self.canned = canned or {}
        self.queries_seen: list[str] = []

    async def search(self, query: str, max_results: int = 5) -> list[WebSearchResult]:
        self.queries_seen.append(query)
        for known_query, results in self.canned.items():
            if known_query.lower() in query.lower():
                return results[:max_results]
        return []
