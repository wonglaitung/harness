"""
FetchGitHubTrendingTool - SDK Tool for GitHub Trending.

Wraps the existing GitHubTrendingSource as an SDK Tool.
"""

import logging
import re
from typing import Any

import aiohttp

from harness.tools.base import Tool, ToolContext
from harness.types import ToolResult

logger = logging.getLogger(__name__)

GITHUB_TRENDING_URL = "https://github.com/trending"

# AI-related keywords for filtering
AI_KEYWORDS = [
    "ai", "llm", "gpt", "claude", "openai", "anthropic",
    "machine-learning", "deep-learning", "neural-network",
    "transformer", "rag", "agent", "mcp", "langchain",
    "embeddings", "vector", "lora", "fine-tuning",
    "inference", "vllm", "ollama", "llama", "mistral",
]


class FetchGitHubTrendingTool(Tool):
    """Fetch trending AI repositories from GitHub."""

    @property
    def name(self) -> str:
        return "fetch_github_trending"

    @property
    def description(self) -> str:
        return "Fetch trending AI-related repositories from GitHub. Filters for AI projects by default."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "language": {
                    "type": "string",
                    "description": "Programming language filter (e.g., 'python', 'typescript'). Default: 'python'",
                },
                "since": {
                    "type": "string",
                    "description": "Time range: 'daily', 'weekly', or 'monthly'. Default: 'daily'",
                },
                "filter_ai": {
                    "type": "boolean",
                    "description": "Filter for AI-related repos only. Default: true",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of repos to return. Default: 15",
                },
            },
            "required": [],
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        language = arguments.get("language", "python")
        since = arguments.get("since", "daily")
        filter_ai = arguments.get("filter_ai", True)
        limit = arguments.get("limit", 15)

        try:
            async with aiohttp.ClientSession() as session:
                url = f"{GITHUB_TRENDING_URL}/{language}?since={since}"
                headers = {
                    "User-Agent": "Mozilla/5.0 (compatible; HarnessScraper/1.0)",
                    "Accept": "text/html",
                }

                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        return ToolResult(
                            tool_call_id="",
                            success=False,
                            content="",
                            error=f"GitHub trending fetch failed: HTTP {resp.status}",
                        )
                    html = await resp.text()

            # Parse trending repos
            repos = self._parse_trending_html(html, filter_ai)

            # Format results
            results = []
            for repo in repos[:limit]:
                results.append(
                    f"Repo: {repo['full_name']}\n"
                    f"URL: {repo['url']}\n"
                    f"Description: {repo['description']}\n"
                    f"Stars today: {repo['stars_today']}\n---"
                )

            content = f"Fetched {len(results)} trending {language} repos:\n\n" + "\n".join(results)

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
                error=f"GitHub trending fetch error: {str(e)}",
            )

    def _parse_trending_html(self, html: str, filter_ai: bool) -> list[dict[str, Any]]:
        """Parse GitHub trending HTML to extract repo info."""
        repos = []

        article_pattern = r'<article[^>]*class="Box-row"[^>]*>(.*?)</article>'

        for match in re.finditer(article_pattern, html, re.DOTALL):
            article_html = match.group(1)

            # Extract repo link
            href_pattern = r'href="/([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)"'
            all_hrefs = re.findall(href_pattern, article_html)

            # Filter out non-repo links
            full_name = None
            for href in all_hrefs:
                if not any(href.startswith(prefix) for prefix in ["sponsors/", "apps/", "trending/", "login", "site/"]):
                    full_name = href
                    break

            if not full_name:
                continue

            # Extract description
            desc_match = re.search(r'<p[^>]*class="col-9[^"]*"[^>]*>(.*?)</p>', article_html, re.DOTALL)
            description = ""
            if desc_match:
                description = re.sub(r"<[^>]+>", "", desc_match.group(1)).strip()

            # Extract stars today
            stars_match = re.search(r"([0-9,]+)\s*stars?\s*today", article_html, re.IGNORECASE)
            stars_today = 0
            if stars_match:
                stars_today = int(stars_match.group(1).replace(",", ""))

            repo = {
                "full_name": full_name,
                "description": description,
                "stars_today": stars_today,
                "url": f"https://github.com/{full_name}",
            }

            # Filter for AI repos
            if filter_ai:
                text_to_check = (description + " " + full_name).lower()
                if not any(kw in text_to_check for kw in AI_KEYWORDS):
                    continue

            repos.append(repo)

        return repos