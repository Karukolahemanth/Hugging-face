"""
Web search tool.
Abstracts over multiple search providers (Tavily, Serper, DuckDuckGo).
Provider is chosen via SEARCH_PROVIDER env variable.
"""

import httpx
from backend.tools.base import BaseTool, ToolResult
from backend.utils.config import get_settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


# ── Provider implementations ──────────────────────────────────────────────────

async def _search_tavily(query: str, api_key: str, max_results: int) -> list[dict]:
    """Search using the Tavily API."""
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    results = []
    for item in data.get("results", []):
        results.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", "")[:500],
            }
        )
    return results


async def _search_serper(query: str, api_key: str, max_results: int) -> list[dict]:
    """Search using the Serper.dev API (Google results)."""
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": max_results}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    results = []
    for item in data.get("organic", []):
        results.append(
            {
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", "")[:500],
            }
        )
    return results


async def _search_duckduckgo(query: str, max_results: int) -> list[dict]:
    """Fallback search using DuckDuckGo HTML (no API key required)."""
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    {
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", "")[:500],
                    }
                )
        return results
    except ImportError:
        return []
    except Exception as exc:
        logger.warning("DuckDuckGo search failed: %s", exc)
        return []


# ── Tool ─────────────────────────────────────────────────────────────────────

class WebSearchTool(BaseTool):
    """Searches the web and returns structured results."""

    name = "web_search"
    description = (
        "Searches the web for up-to-date information. "
        "Returns a list of relevant results with title, URL, and snippet. "
        "Use this to find current facts, news, statistics, or any information "
        "not in your training data."
    )

    async def execute(self, arguments: dict) -> ToolResult:
        query: str = arguments.get("query", "").strip()
        max_results: int = int(arguments.get("max_results", 5))

        if not query:
            return ToolResult(success=False, error="No search query provided.")

        settings = get_settings()
        provider = settings.search_provider.lower() if settings.search_provider else ""
        api_key = settings.search_api_key

        logger.info("WebSearch [%s]: %s", provider or "duckduckgo", query)

        try:
            if provider == "tavily" and api_key:
                results = await _search_tavily(query, api_key, max_results)
            elif provider == "serper" and api_key:
                results = await _search_serper(query, api_key, max_results)
            else:
                # Default: DuckDuckGo (free, no key needed)
                results = await _search_duckduckgo(query, max_results)

            if not results:
                return ToolResult(
                    success=True,
                    result={"query": query, "results": []},
                    metadata={"provider": provider or "duckduckgo", "count": 0},
                )

            return ToolResult(
                success=True,
                result={"query": query, "results": results},
                metadata={"provider": provider or "duckduckgo", "count": len(results)},
            )

        except Exception as exc:
            logger.error("WebSearch failed: %s", exc)
            return ToolResult(success=False, error=f"Search failed: {exc}")

    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up on the web.",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 5, max: 10).",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        }


# Singleton instance
web_search_tool = WebSearchTool()
