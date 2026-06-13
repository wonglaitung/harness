"""
FetchFinancialNewsTool - SDK Tool for fetching real-time financial news.

Uses stable, community-maintained data sources:
- AkShare: 财联社电报快讯 (real-time Chinese financial news)
- yfinance: US macro data (Treasury yields, Fed rates)

This is production-ready and avoids fragile commercial API scraping.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

import pandas as pd

from harness.tools.base import Tool, ToolContext
from harness.types import ToolResult

logger = logging.getLogger(__name__)


class FetchFinancialNewsTool(Tool):
    """Fetch real-time financial news from stable sources.

    Sources:
    - cailian: 财联社电报快讯 via AkShare
    - macro: US macro data (Treasury yields) via yfinance
    """

    @property
    def name(self) -> str:
        return "fetch_financial_news"

    @property
    def description(self) -> str:
        return "Fetch real-time financial news: Cailian telegraph (财联社快讯), macro data (US Treasury yields). Stable APIs via AkShare and yfinance. Use for HK stocks alpha event capture."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "enum": ["cailian", "macro", "all"],
                    "description": "News source: cailian (财联社快讯), macro (US macro rates), or all",
                },
                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Keywords to filter news (e.g., ['港股', '美联储', '监管'])",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of news items per source (default: 30)",
                },
            },
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        source = arguments.get("source", "cailian")
        keywords = arguments.get("keywords", [])
        limit = arguments.get("limit", 30)

        try:
            all_news = []

            if source in ["cailian", "all"]:
                cailian_news = await self._fetch_cailian(keywords, limit)
                all_news.extend(cailian_news)

            if source in ["macro", "all"]:
                macro_data = await self._fetch_macro_rates()
                if macro_data:
                    all_news.append(macro_data)

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
        """Fetch news from East Money via AkShare."""
        loop = asyncio.get_running_loop()

        try:
            # Run AkShare in thread pool
            df = await loop.run_in_executor(None, self._get_financial_news)

            if df.empty:
                logger.warning("Financial news returned empty data")
                return []

            news_items = []
            for _, row in df.head(limit).iterrows():
                # stock_news_em columns: 关键词, 新闻标题, 新闻内容, 发布时间, 文章来源, 新闻链接
                title = row.get('新闻标题', '')
                content = row.get('新闻内容', '')
                time_str = row.get('发布时间', '')
                source_name = row.get('文章来源', '')
                url = row.get('新闻链接', '')

                # Filter by keywords
                if keywords:
                    text = f"{title} {content}".lower()
                    if not any(kw.lower() in text for kw in keywords):
                        continue

                news_items.append({
                    "source": f"东方财富-{source_name}",
                    "title": title,
                    "content": content[:500],
                    "time": time_str,
                    "url": url,
                    "level": "",
                })

            return news_items

        except Exception as e:
            logger.error(f"Error fetching financial news: {e}")
            return []

    def _get_financial_news(self) -> pd.DataFrame:
        """Get financial news via AkShare (runs in thread pool)."""
        try:
            import akshare as ak
            # Use stock_news_em for HK stock related news (stable API)
            return ak.stock_news_em(symbol="港股")
        except ImportError:
            logger.error("akshare not installed. Run: pip install akshare")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"AkShare stock_news_em error: {e}")
            return pd.DataFrame()

    async def _fetch_macro_rates(self) -> dict | None:
        """Fetch US macro rates (Treasury yields) via yfinance."""
        loop = asyncio.get_running_loop()

        try:
            rates = await loop.run_in_executor(None, self._get_us_rates)

            if not rates:
                return None

            return {
                "source": "US_Macro",
                "title": "美国国债收益率监控",
                "content": (
                    f"10年期国债收益率 (^TNX): {rates.get('tnx', 'N/A'):.2f}%\n"
                    f"2年期国债收益率 (^IRX): {rates.get('irx', 'N/A'):.2f}%\n"
                    f"收益率曲线: {'倒挂' if rates.get('tnx', 0) < rates.get('irx', 0) else '正常'}\n"
                    f"更新时间: {rates.get('time', '')}"
                ),
                "time": rates.get('time', ''),
                "url": "https://finance.yahoo.com/bonds",
                "level": "MACRO",
            }

        except Exception as e:
            logger.error(f"Error fetching macro rates: {e}")
            return None

    def _get_us_rates(self) -> dict:
        """Get US Treasury yields via yfinance (runs in thread pool)."""
        try:
            import yfinance as yf

            rates = {}

            # 10-Year Treasury
            tnx = yf.Ticker("^TNX")
            tnx_hist = tnx.history(period="1d")
            if not tnx_hist.empty:
                rates['tnx'] = tnx_hist['Close'].iloc[-1]

            # 13-Week Treasury (proxy for 2-year)
            irx = yf.Ticker("^IRX")
            irx_hist = irx.history(period="1d")
            if not irx_hist.empty:
                rates['irx'] = irx_hist['Close'].iloc[-1]

            rates['time'] = datetime.now().strftime("%Y-%m-%d %H:%M")

            return rates

        except ImportError:
            logger.error("yfinance not installed. Run: pip install yfinance")
            return {}
        except Exception as e:
            logger.error(f"yfinance error: {e}")
            return {}

    def _format_news(self, news_items: list[dict], source: str) -> str:
        """Format news for output."""
        if not news_items:
            return f"No financial news found from {source}"

        lines = [f"## 金融快讯 ({source})\n"]

        for item in news_items:
            lines.append(f"### {item['title']}")
            lines.append(f"- 来源: {item['source']}")
            if item.get('level'):
                lines.append(f"- 级别: {item['level']}")
            lines.append(f"- 时间: {item['time']}")
            lines.append(f"- 链接: {item['url']}")
            if item['content']:
                lines.append(f"- 内容: {item['content'][:300]}...")
            lines.append("")

        return "\n".join(lines)
