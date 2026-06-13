"""
FetchHKEXTool - SDK Tool for fetching HKEX announcements.

Fetches announcements from Hong Kong Stock Exchange:
- Buyback announcements (股份回购)
- Insider trading disclosures (内幕交易披露)
- Major announcements (重大公告)
"""

import asyncio
import logging
import re
from typing import Any

import aiohttp

from harness.tools.base import Tool, ToolContext
from harness.types import ToolResult

logger = logging.getLogger(__name__)

# HKEX News RSS feed
HKEX_RSS_URL = "https://www.hkexnews.hk/RSS.aspx?language=zh-CN"


class FetchHKEXTool(Tool):
    """Fetch HKEX announcements: buybacks, insider trading, major disclosures."""

    @property
    def name(self) -> str:
        return "fetch_hkex"

    @property
    def description(self) -> str:
        return "Fetch HKEX (Hong Kong Stock Exchange) announcements: buybacks, insider trading, major disclosures. Use this to find stock repurchases, insider trades, and important company announcements."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "stock_code": {
                    "type": "string",
                    "description": "Stock code to filter (e.g., '00700' for Tencent). Leave empty for all stocks.",
                },
                "announcement_type": {
                    "type": "string",
                    "enum": ["buyback", "insider", "major", "all"],
                    "description": "Type of announcement to filter: buyback (回购), insider (内幕交易), major (重大公告), all (全部)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of announcements to return (default: 20)",
                },
            },
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        stock_code = arguments.get("stock_code", "")
        announcement_type = arguments.get("announcement_type", "all")
        limit = arguments.get("limit", 20)

        try:
            # Fetch HKEX RSS feed
            announcements = await self._fetch_hkex_rss(limit=limit * 2)

            # Filter by stock code and type
            filtered = []
            for ann in announcements:
                if stock_code and stock_code not in ann.get("stock_code", ""):
                    continue
                if announcement_type != "all":
                    if not self._match_type(ann, announcement_type):
                        continue
                filtered.append(ann)
                if len(filtered) >= limit:
                    break

            # Format output
            content = self._format_announcements(filtered, announcement_type)

            return ToolResult(
                tool_call_id="",
                success=True,
                content=content,
            )

        except Exception as e:
            logger.error(f"Failed to fetch HKEX announcements: {e}")
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Failed to fetch HKEX announcements: {str(e)}",
            )

    async def _fetch_hkex_rss(self, limit: int = 50) -> list[dict]:
        """Fetch HKEX RSS feed and parse announcements."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(HKEX_RSS_URL, timeout=30) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status}")

                    content = await response.text()

            # Parse RSS XML
            import xml.etree.ElementTree as ET

            root = ET.fromstring(content)
            announcements = []

            for item in root.findall(".//item")[:limit]:
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                pub_date = item.findtext("pubDate", "")
                description = item.findtext("description", "")

                # Extract stock code from title (format: "00700 腾讯控股 - 股份回购")
                stock_code_match = re.match(r"(\d{5})", title)
                stock_code = stock_code_match.group(1) if stock_code_match else ""

                announcements.append({
                    "title": title,
                    "link": link,
                    "pub_date": pub_date,
                    "description": description[:500] if description else "",
                    "stock_code": stock_code,
                    "type": self._detect_type(title, description),
                })

            return announcements

        except Exception as e:
            logger.error(f"Error fetching HKEX RSS: {e}")
            return []

    def _detect_type(self, title: str, description: str) -> str:
        """Detect announcement type from title/description."""
        text = f"{title} {description}".lower()

        buyback_keywords = ["回购", "buyback", "repurchase", "购回"]
        insider_keywords = ["内幕", "insider", "董事", "director", "持股", "shareholding"]

        for kw in buyback_keywords:
            if kw in text:
                return "buyback"
        for kw in insider_keywords:
            if kw in text:
                return "insider"
        return "major"

    def _match_type(self, announcement: dict, target_type: str) -> bool:
        """Check if announcement matches target type."""
        return announcement.get("type") == target_type

    def _format_announcements(self, announcements: list[dict], ann_type: str) -> str:
        """Format announcements for output."""
        if not announcements:
            return f"No HKEX announcements found for type: {ann_type}"

        lines = [f"## HKEX Announcements ({ann_type})\n"]

        for ann in announcements:
            lines.append(f"### {ann['title']}")
            lines.append(f"- 股票代码: {ann['stock_code']}")
            lines.append(f"- 类型: {ann['type']}")
            lines.append(f"- 发布时间: {ann['pub_date']}")
            lines.append(f"- 链接: {ann['link']}")
            if ann['description']:
                lines.append(f"- 摘要: {ann['description'][:200]}...")
            lines.append("")

        return "\n".join(lines)
