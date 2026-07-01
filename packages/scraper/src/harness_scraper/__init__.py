"""
Harness Scraper - AI Intelligence Extraction System.

Goal-driven intelligence extraction from web sources:
- Tools: fetch_rss, fetch_hn, fetch_show_hn, fetch_github_trending, fetch_url, save_one_pager
- GoalAgent: Goal-driven execution using run_goal()
- IntelAgent: One-shot execution using run()
- Skills: Domain-specific intelligence extraction (AI, stocks, etc.)
- Output: One-Pager markdown files
"""

from harness_scraper.agent import IntelAgent, load_skill
from harness_scraper.goal_agent import GoalAgent
from harness_scraper.models import ScraperConfig
from harness_scraper.tools import (
    FetchRSSTool,
    FetchHNTool,
    FetchShowHNTool,
    FetchGitHubTrendingTool,
    FetchURLTool,
    SaveOnePagerTool,
)

__version__ = "0.4.0"
__all__ = [
    "GoalAgent",
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
