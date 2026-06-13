"""
Source module - Data source abstractions.
"""

from harness_scraper.sources.base import Source
from harness_scraper.sources.github_trending import GitHubTrendingSource
from harness_scraper.sources.hacker_news import HackerNewsSource, ShowHNSource

__all__ = ["Source", "GitHubTrendingSource", "HackerNewsSource", "ShowHNSource"]