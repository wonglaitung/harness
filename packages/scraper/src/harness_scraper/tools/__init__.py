"""
Scraper Tools - SDK Tool wrappers for data sources.

These tools can be used by AgentHarness to fetch and process content.

AI Intelligence Tools:
- FetchRSSTool: RSS feeds
- FetchHNTool: Hacker News posts
- FetchShowHNTool: Show HN early projects
- FetchGitHubTrendingTool: GitHub trending repos
- FetchURLTool: Deep content fetching

Stock/Financial Tools:
- FetchHKEXTool: Hong Kong Stock Exchange announcements
- FetchFinancialNewsTool: Real-time financial news (Cailian, Wallstreetcn)

Output Tools:
- SaveOnePagerTool: Save intelligence One-Pager
- UpdateMemoryTool: Record processed items to MEMORY.md
- ReadHistoryReportTool: Read historical One-Pager reports for trend analysis
"""

from harness_scraper.tools.fetch_rss import FetchRSSTool
from harness_scraper.tools.fetch_hn import FetchHNTool, FetchShowHNTool
from harness_scraper.tools.fetch_github_trending import FetchGitHubTrendingTool
from harness_scraper.tools.fetch_url import FetchURLTool
from harness_scraper.tools.save_one_pager import SaveOnePagerTool
from harness_scraper.tools.update_memory import UpdateMemoryTool
from harness_scraper.tools.read_history_report import ReadHistoryReportTool

# Stock/Financial Tools
from harness_scraper.tools.fetch_hkex import FetchHKEXTool
from harness_scraper.tools.fetch_financial_news import FetchFinancialNewsTool

from harness.tools.base import Tool

__all__ = [
    # AI Intelligence Tools
    "FetchRSSTool",
    "FetchHNTool",
    "FetchShowHNTool",
    "FetchGitHubTrendingTool",
    "FetchURLTool",
    "SaveOnePagerTool",
    "UpdateMemoryTool",
    "ReadHistoryReportTool",
    # Stock/Financial Tools
    "FetchHKEXTool",
    "FetchFinancialNewsTool",
    # Tool registry
    "ALL_TOOLS",
    "get_tools_by_names",
]

# Tool registry: name -> class (not instance)
ALL_TOOLS: dict[str, type[Tool]] = {
    "fetch_rss": FetchRSSTool,
    "fetch_hn": FetchHNTool,
    "fetch_show_hn": FetchShowHNTool,
    "fetch_github_trending": FetchGitHubTrendingTool,
    "fetch_url": FetchURLTool,
    "save_one_pager": SaveOnePagerTool,
    "update_memory": UpdateMemoryTool,
    "read_history_report": ReadHistoryReportTool,
    "fetch_hkex": FetchHKEXTool,
    "fetch_financial_news": FetchFinancialNewsTool,
}


def get_tools_by_names(tool_names: list[str]) -> list[Tool]:
    """
    Get tool instances by their names.

    Args:
        tool_names: List of tool names (e.g., ["fetch_rss", "fetch_hn"])

    Returns:
        List of Tool instances

    Raises:
        ValueError: If any tool name is not found in ALL_TOOLS
    """
    tools: list[Tool] = []
    missing: list[str] = []

    for name in tool_names:
        tool_class = ALL_TOOLS.get(name)
        if tool_class:
            tools.append(tool_class())
        else:
            missing.append(name)

    if missing:
        raise ValueError(f"Unknown tools: {missing}. Available: {list(ALL_TOOLS.keys())}")

    return tools
