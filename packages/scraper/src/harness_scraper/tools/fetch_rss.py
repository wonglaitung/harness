"""
FetchRSSTool - SDK Tool for RSS feed fetching.

Wraps the existing RSSSource as an SDK Tool.
"""

from typing import Any

import feedparser

from harness.tools.base import Tool, ToolContext
from harness.types import ToolResult


class FetchRSSTool(Tool):
    """Fetch articles from RSS feeds."""

    @property
    def name(self) -> str:
        return "fetch_rss"

    @property
    def description(self) -> str:
        return "Fetch articles from an RSS feed URL. Returns a list of articles with title, content, and URL."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "RSS feed URL to fetch",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of articles to return (default: 30)",
                },
            },
            "required": ["url"],
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        import aiohttp

        url = arguments["url"]
        limit = arguments.get("limit", 30)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        return ToolResult(
                            tool_call_id="",
                            success=False,
                            content="",
                            error=f"RSS fetch failed: HTTP {resp.status}",
                        )
                    content = await resp.text()

            # Parse feed
            feed = feedparser.parse(content)

            if feed.bozo and not feed.entries:
                return ToolResult(
                    tool_call_id="",
                    success=False,
                    content="",
                    error=f"RSS parse error: {feed.bozo_exception}",
                )

            # Format results
            articles = []
            for entry in feed.entries[:limit]:
                title = entry.get("title", "Untitled")
                link = entry.get("link", "")
                summary = entry.get("summary", "")

                # Clean HTML from summary
                import re
                summary = re.sub(r"<[^>]+>", " ", summary)
                summary = re.sub(r"\s+", " ", summary).strip()[:500]

                articles.append(f"Title: {title}\nURL: {link}\nSummary: {summary}\n---")

            content = f"Fetched {len(articles)} articles from RSS feed:\n\n" + "\n".join(articles)

            return ToolResult(
                tool_call_id="",
                success=True,
                content=content,
            )

        except Exception as e:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"RSS fetch error: {str(e)}",
            )