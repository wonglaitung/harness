"""
Harness Scraper - AI Intelligence Extraction System.

SDK Agent-based intelligence extraction from web sources:
- Tools: fetch_rss, fetch_hn, fetch_show_hn, fetch_github_trending, fetch_url, save_one_pager
- Agent: IntelAgent powered by AgentHarness
- Skills: Domain-specific intelligence extraction (AI, stocks, etc.)
- Output: One-Pager markdown files
"""

from harness_scraper.agent import IntelAgent, load_skill
from harness_scraper.models import ScraperConfig
from harness_scraper.tools import (
    FetchRSSTool,
    FetchHNTool,
    FetchShowHNTool,
    FetchGitHubTrendingTool,
    FetchURLTool,
    SaveOnePagerTool,
)

__version__ = "0.3.0"
__all__ = [
    "IntelAgent",
    "load_skill",
    "ScraperConfig",
    "FetchRSSTool",
    "FetchHNTool",
    "FetchShowHNTool",
    "FetchGitHubTrendingTool",
    "FetchURLTool",
    "SaveOnePagerTool",
]
