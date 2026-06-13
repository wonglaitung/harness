"""
FetchHKEXTool - SDK Tool for fetching HK stock market data via AkShare.

Uses AkShare's stable APIs (东方财富源) instead of fragile HKEX web scraping:
- Real-time HK stock quotes and movements
- High volume / significant price changes
- Major announcements

This is production-ready and maintained by the open source community.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

import pandas as pd

from harness.tools.base import Tool, ToolContext
from harness.types import ToolResult

logger = logging.getLogger(__name__)

# Default volume threshold: 50M HKD
DEFAULT_VOLUME_THRESHOLD = 50_000_000
# Default price change threshold: 3%
DEFAULT_PCT_THRESHOLD = 3.0


class FetchHKEXTool(Tool):
    """Fetch HK stock market data: real-time quotes, significant movements, high volume stocks.

    Uses AkShare (东方财富源) which is stable and community-maintained.
    """

    @property
    def name(self) -> str:
        return "fetch_hkex"

    @property
    def description(self) -> str:
        return "Fetch Hong Kong stock market data: real-time quotes, significant price movements, and high volume stocks. Uses stable AkShare APIs. Returns stocks with major movements for LLM analysis."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "volume_threshold": {
                    "type": "integer",
                    "description": "Minimum trading volume in HKD (default: 50000000 = 50M)",
                },
                "pct_threshold": {
                    "type": "number",
                    "description": "Minimum absolute price change % (default: 3.0)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of stocks to return (default: 20)",
                },
                "focus_codes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Focus on specific stock codes (e.g., ['00700', '03690'])",
                },
            },
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        volume_threshold = arguments.get("volume_threshold", DEFAULT_VOLUME_THRESHOLD)
        pct_threshold = arguments.get("pct_threshold", DEFAULT_PCT_THRESHOLD)
        limit = arguments.get("limit", 20)
        focus_codes = arguments.get("focus_codes", [])

        try:
            # Fetch HK stock data via AkShare
            stocks = await self._fetch_hk_stocks(
                volume_threshold=volume_threshold,
                pct_threshold=pct_threshold,
                focus_codes=focus_codes,
                limit=limit,
            )

            # Format output
            content = self._format_stocks(stocks)

            return ToolResult(
                tool_call_id="",
                success=True,
                content=content,
            )

        except Exception as e:
            logger.error(f"Failed to fetch HK stock data: {e}")
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Failed to fetch HK stock data: {str(e)}",
            )

    async def _fetch_hk_stocks(
        self,
        volume_threshold: int,
        pct_threshold: float,
        focus_codes: list[str],
        limit: int,
    ) -> list[dict]:
        """Fetch HK stock data using AkShare in thread pool."""
        loop = asyncio.get_running_loop()

        try:
            # Run AkShare in thread pool (it's synchronous)
            df = await loop.run_in_executor(None, self._get_hk_spot_data)

            if df.empty:
                logger.warning("AkShare returned empty data")
                return []

            # Clean data
            df = self._clean_dataframe(df)

            # Filter by volume
            df = df[df['成交额'] >= volume_threshold]

            # Filter by price change
            df = df[df['涨跌幅'].abs() >= pct_threshold]

            # Filter by focus codes if specified
            if focus_codes:
                df = df[df['代码'].isin(focus_codes)]

            # Sort by volume descending
            df = df.sort_values('成交额', ascending=False)

            # Limit results
            df = df.head(limit)

            # Convert to list of dicts
            stocks = []
            for _, row in df.iterrows():
                stocks.append({
                    "code": row['代码'],
                    "name": row['名称'],
                    "price": row['最新价'],
                    "pct_change": row['涨跌幅'],
                    "volume": row['成交额'],
                    "turnover_rate": row.get('换手率', 0),
                    "url": f"https://guba.eastmoney.com/list,hk{row['代码']}.html",
                })

            return stocks

        except Exception as e:
            logger.error(f"Error in _fetch_hk_stocks: {e}")
            return []

    def _get_hk_spot_data(self) -> pd.DataFrame:
        """Get HK stock spot data via AkShare (runs in thread pool)."""
        try:
            import akshare as ak
            return ak.stock_hk_spot_em()
        except ImportError:
            logger.error("akshare not installed. Run: pip install akshare")
            return pd.DataFrame()

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and convert dataframe columns."""
        # Convert numeric columns
        df['成交额'] = pd.to_numeric(df['成交额'], errors='coerce').fillna(0)
        df['涨跌幅'] = pd.to_numeric(df['涨跌幅'], errors='coerce').fillna(0)
        df['最新价'] = pd.to_numeric(df['最新价'], errors='coerce').fillna(0)

        return df

    def _format_stocks(self, stocks: list[dict]) -> str:
        """Format stocks for output."""
        if not stocks:
            return "No significant HK stock movements found matching criteria."

        lines = ["## 港股异动监控\n"]

        for stock in stocks:
            direction = "📈" if stock['pct_change'] > 0 else "📉"
            lines.append(f"### {direction} {stock['name']} ({stock['code']}.HK)")
            lines.append(f"- 最新价: {stock['price']:.2f} 港元")
            lines.append(f"- 涨跌幅: **{stock['pct_change']:.2f}%**")
            lines.append(f"- 成交额: {stock['volume']/1_000_000:.1f} 百万港元")
            if stock.get('turnover_rate'):
                lines.append(f"- 换手率: {stock['turnover_rate']:.2f}%")
            lines.append(f"- 股吧: {stock['url']}")
            lines.append("")

        lines.append(f"\n**共 {len(stocks)} 只个股发生显著异动，请结合宏观消息面分析。**")

        return "\n".join(lines)
