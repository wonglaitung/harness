"""
FetchURLTool - SDK Tool for fetching URL content (GitHub README + Jina Reader).

Deep explorer for fetching detailed content from URLs.
"""

import logging
import re
from typing import Any

import aiohttp

from harness.tools.base import Tool, ToolContext
from harness.types import ToolResult

logger = logging.getLogger(__name__)

# README file names to try (in order)
README_NAMES = ["README.md", "README.rst", "README.txt", "readme.md", "docs/index.md"]


class FetchURLTool(Tool):
    """Fetch content from a URL, with special handling for GitHub repos."""

    @property
    def name(self) -> str:
        return "fetch_url"

    @property
    def description(self) -> str:
        return "Fetch content from a URL. For GitHub repos, fetches the README. For other URLs, uses Jina Reader API for clean extraction."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to fetch content from",
                },
                "max_length": {
                    "type": "integer",
                    "description": "Maximum content length in characters (default: 10000)",
                },
            },
            "required": ["url"],
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        url = arguments["url"]
        max_length = arguments.get("max_length", 10000)

        try:
            # Check if it's a GitHub URL
            if "github.com" in url:
                content = await self._fetch_github_readme(url)
                if content:
                    return ToolResult(
                        tool_call_id="",
                        success=True,
                        content=content[:max_length],
                    )

            # Fallback to Jina Reader
            content = await self._fetch_jina_reader(url)
            if content:
                return ToolResult(
                    tool_call_id="",
                    success=True,
                    content=content[:max_length],
                )

            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Could not fetch content from {url}",
            )

        except Exception as e:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"URL fetch error: {str(e)}",
            )

    async def _fetch_github_readme(self, url: str) -> str | None:
        """Fetch README from a GitHub repo URL."""
        # Parse owner/repo from URL
        match = re.search(r"github\.com/([^/]+/[^/]+)", url)
        if not match:
            return None

        repo = match.group(1).rstrip("/")

        async with aiohttp.ClientSession() as session:
            # Try different README names and branches
            for branch in ["main", "master"]:
                for readme_name in README_NAMES:
                    raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{readme_name}"
                    try:
                        async with session.get(raw_url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                            if resp.status == 200:
                                content = await resp.text()
                                logger.info(f"Fetched README from {raw_url}")
                                return content
                    except Exception:
                        continue

        return None

    async def _fetch_jina_reader(self, url: str) -> str | None:
        """Fetch content using Jina Reader API."""
        jina_url = f"https://r.jina.ai/{url}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    jina_url,
                    timeout=aiohttp.ClientTimeout(total=30),
                    headers={"User-Agent": "Mozilla/5.0 (compatible; HarnessScraper/1.0)"},
                ) as resp:
                    if resp.status == 200:
                        content = await resp.text()
                        logger.info(f"Fetched content via Jina Reader from {url}")
                        return content
            except Exception as e:
                logger.warning(f"Jina Reader fetch failed: {e}")

        return None