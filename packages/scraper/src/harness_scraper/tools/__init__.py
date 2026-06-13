"""
Scraper Tools - SDK Tool wrappers for data sources.

These tools can be used by AgentHarness to fetch and process content.
"""

from harness_scraper.tools.fetch_rss import FetchRSSTool
from harness_scraper.tools.fetch_hn import FetchHNTool, FetchShowHNTool
from harness_scraper.tools.fetch_github_trending import FetchGitHubTrendingTool
from harness_scraper.tools.fetch_url import FetchURLTool
from harness_scraper.tools.save_one_pager import SaveOnePagerTool

__all__ = [
    "FetchRSSTool",
    "FetchHNTool",
    "FetchShowHNTool",
    "FetchGitHubTrendingTool",
    "FetchURLTool",
    "SaveOnePagerTool",
]
