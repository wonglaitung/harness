"""
FetchFinancialNewsTool - SDK Tool for fetching real-time financial news.

Fetches news from:
- Cailian Press (财联社) - Chinese financial news
- Wallstreetcn (华尔街见闻) - Global market news
- Bloomberg - International financial news
"""

import asyncio
import logging
from typing import Any

import aiohttp

from harness.tools.base import Tool, ToolContext
from harness.types import ToolResult

logger = logging.getLogger(__name__)

# News sources
NEWS_SOURCES = {
    "cailian": {
        "name": "财联社",
        "api_url": "https://www.cls.cn/api/sw",
        "description": "中国财经快讯，政策突发，A/H联动",
    },
    "wallstreetcn": {
        "name": "华尔街见闻",
        "api_url": "https://wallstreetcn.com/news/global",
        "description": "全球市场新闻，美联储，宏观政策",
    },
    "bloomberg": {
        "name": "Bloomberg",
        "api_url": "https://www.bloomberg.com/feed",
        "description": "国际财经新闻",
    },
}


class FetchFinancialNewsTool(Tool):
    """Fetch real-time financial news from Cailian, Wallstreetcn, Bloomberg."""

    @property
    def name(self) -> str:
        return "fetch_financial_news"

    @property
    def description(self) -> str:
        return "Fetch real-time financial news from Chinese and global sources. Use this to find policy changes, Fed decisions, market-moving events. Sources: cailian (财联社), wallstreetcn (华尔街见闻), bloomberg."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "enum": ["cailian", "wallstreetcn", "bloomberg", "all"],
                    "description": "News source: cailian (财联社), wallstreetcn (华尔街见闻), bloomberg, or all",
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keywords to filter news (e.g., ['港股', '美联储', '监管'])",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of news items to return per source (default: 20)",
                },
            },
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        source = arguments.get("source", "all")
        keywords = arguments.get("keywords", [])
        limit = arguments.get("limit", 20)

        try:
            all_news = []

            if source == "all":
                # Fetch from all sources
                tasks = [
                    self._fetch_cailian(keywords, limit),
                    self._fetch_wallstreetcn(keywords, limit),
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, list):
                        all_news.extend(result)
            elif source == "cailian":
                all_news = await self._fetch_cailian(keywords, limit)
            elif source == "wallstreetcn":
                all_news = await self._fetch_wallstreetcn(keywords, limit)
            else:
                return ToolResult(
                    tool_call_id="",
                    success=False,
                    content="",
                    error=f"Source '{source}' not yet implemented. Use 'cailian' or 'wallstreetcn'.",
                )

            # Format output
            content = self._format_news(all_news, source)

            return ToolResult(
                tool_call_id="",
                success=True,
                content=content,
            )

        except Exception as e:
            logger.error(f"Failed to fetch financial news: {e}")
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Failed to fetch financial news: {str(e)}",
            )

    async def _fetch_cailian(self, keywords: list[str], limit: int) -> list[dict]:
        """Fetch news from Cailian Press (财联社)."""
        try:
            # Cailian API endpoint
            url = "https://www.cls.cn/api/sw"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            }

            # Request body for fetching latest news
            payload = {
                "app": "CailianpressWeb",
                "os": "web",
                "sv": "8.4.6",
                "sign": "",  # API signature (may need updating)
            }

            async with aiohttp.ClientSession() as session:
                # Try fetching via their public API
                async with session.get(
                    "https://www.cls.cn/nodeapi/telegraphs",
                    headers=headers,
                    timeout=15,
                ) as response:
                    if response.status != 200:
                        logger.warning(f"Cailian API returned {response.status}")
                        return []

                    data = await response.json()

            # Parse response
            news_items = []
            items = data.get("data", {}).get("roll_data", [])[:limit]

            for item in items:
                title = item.get("title", "") or item.get("content", "")[:100]
                content = item.get("content", "")

                # Filter by keywords
                if keywords:
                    text = f"{title} {content}".lower()
                    if not any(kw.lower() in text for kw in keywords):
                        continue

                news_items.append({
                    "source": "财联社",
                    "title": title,
                    "content": content[:500],
                    "time": item.get("ctime", ""),
                    "url": f"https://www.cls.cn/detail/{item.get('id', '')}",
                    "level": item.get("level", ""),  # Importance level
                })

            return news_items

        except Exception as e:
            logger.error(f"Error fetching Cailian news: {e}")
            return []

    async def _fetch_wallstreetcn(self, keywords: list[str], limit: int) -> list[dict]:
        """Fetch news from Wallstreetcn (华尔街见闻)."""
        try:
            url = "https://wallstreetcn.com/news/global"

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api-one.wallstreetcn.com/apiv1/content/articles",
                    params={"channel": "global-channel", "limit": limit},
                    headers=headers,
                    timeout=15,
                ) as response:
                    if response.status != 200:
                        logger.warning(f"Wallstreetcn API returned {response.status}")
                        return []

                    data = await response.json()

            # Parse response
            news_items = []
            items = data.get("data", {}).get("items", [])[:limit]

            for item in items:
                title = item.get("title", "")
                content = item.get("content_text", "") or item.get("content", "")

                # Filter by keywords
                if keywords:
                    text = f"{title} {content}".lower()
                    if not any(kw.lower() in text for kw in keywords):
                        continue

                news_items.append({
                    "source": "华尔街见闻",
                    "title": title,
                    "content": content[:500],
                    "time": item.get("display_time", ""),
                    "url": item.get("uri", ""),
                    "level": "",
                })

            return news_items

        except Exception as e:
            logger.error(f"Error fetching Wallstreetcn news: {e}")
            return []

    def _format_news(self, news_items: list[dict], source: str) -> str:
        """Format news for output."""
        if not news_items:
            return f"No financial news found from {source}"

        lines = [f"## Financial News ({source})\n"]

        for item in news_items:
            lines.append(f"### {item['title']}")
            lines.append(f"- 来源: {item['source']}")
            if item['level']:
                lines.append(f"- 重要性: {item['level']}")
            lines.append(f"- 时间: {item['time']}")
            lines.append(f"- 链接: {item['url']}")
            if item['content']:
                lines.append(f"- 内容: {item['content'][:200]}...")
            lines.append("")

        return "\n".join(lines)
