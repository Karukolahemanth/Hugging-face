"""
Webpage reader tool.
Downloads and cleans webpage content using httpx + BeautifulSoup.
"""

import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from backend.tools.base import BaseTool, ToolResult
from backend.utils.logger import get_logger

logger = get_logger(__name__)

MAX_CONTENT_CHARS = 8000   # cap to avoid overwhelming context window
REQUEST_TIMEOUT = 15       # seconds
MAX_DOWNLOAD_BYTES = 2_000_000  # 2 MB max download


class WebpageReaderTool(BaseTool):
    """Downloads a URL and returns cleaned readable text."""

    name = "read_webpage"
    description = (
        "Downloads and reads the textual content of a webpage. "
        "Returns the page title, cleaned text, and important links. "
        "Use this after web_search to read the full content of a search result."
    )

    async def execute(self, arguments: dict) -> ToolResult:
        url: str = arguments.get("url", "").strip()
        if not url:
            return ToolResult(success=False, error="No URL provided.")

        # Basic URL validation
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return ToolResult(
                success=False,
                error=f"Invalid URL scheme '{parsed.scheme}'. Only http/https allowed.",
            )

        logger.info("WebpageReader fetching: %s", url)

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; GAIAAgent/1.0; "
                "+https://github.com/gaia-agent)"
            ),
            "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            async with httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT,
                follow_redirects=True,
                headers=headers,
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()

                # Respect content-type
                content_type = resp.headers.get("content-type", "")
                if "text" not in content_type and "html" not in content_type:
                    return ToolResult(
                        success=False,
                        error=f"Non-text content-type: {content_type}",
                    )

                raw_html = resp.text[:MAX_DOWNLOAD_BYTES]

        except httpx.TimeoutException:
            return ToolResult(success=False, error=f"Request to {url} timed out.")
        except httpx.HTTPStatusError as exc:
            return ToolResult(
                success=False,
                error=f"HTTP {exc.response.status_code} from {url}.",
            )
        except Exception as exc:
            logger.warning("WebpageReader error: %s", exc)
            return ToolResult(success=False, error=str(exc))

        # ── Parse HTML ────────────────────────────────────────────────────
        soup = BeautifulSoup(raw_html, "html.parser")

        # Remove script/style/nav noise
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        title = soup.title.string.strip() if soup.title and soup.title.string else url

        # Extract main text
        text = soup.get_text(separator="\n", strip=True)
        # Collapse excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = text[:MAX_CONTENT_CHARS]

        # Extract links
        links = []
        for a in soup.find_all("a", href=True)[:20]:
            href = a["href"]
            if href.startswith("http"):
                links.append({"text": a.get_text(strip=True)[:80], "url": href})

        return ToolResult(
            success=True,
            result={
                "url": url,
                "title": title,
                "text": text,
                "links": links[:10],
                "char_count": len(text),
            },
        )

    def schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full URL of the webpage to read (must start with http:// or https://).",
                    }
                },
                "required": ["url"],
            },
        }


# Singleton instance
webpage_reader_tool = WebpageReaderTool()
