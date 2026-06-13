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
"""

from harness_scraper.tools.fetch_rss import FetchRSSTool
from harness_scraper.tools.fetch_hn import FetchHNTool, FetchShowHNTool
from harness_scraper.tools.fetch_github_trending import FetchGitHubTrendingTool
from harness_scraper.tools.fetch_url import FetchURLTool
from harness_scraper.tools.save_one_pager import SaveOnePagerTool

# Stock/Financial Tools
from harness_scraper.tools.fetch_hkex import FetchHKEXTool
from harness_scraper.tools.fetch_financial_news import FetchFinancialNewsTool

__all__ = [
    # AI Intelligence Tools
    "FetchRSSTool",
    "FetchHNTool",
    "FetchShowHNTool",
    "FetchGitHubTrendingTool",
    "FetchURLTool",
    "SaveOnePagerTool",
    # Stock/Financial Tools
    "FetchHKEXTool",
    "FetchFinancialNewsTool",
]
