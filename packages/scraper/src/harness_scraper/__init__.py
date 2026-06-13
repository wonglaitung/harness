"""
Harness Scraper - AI Intelligence Extraction System.

Automated scraping and analysis of AI industry trends:
- Sources: RSS, Hacker News, Reddit, X (via RSSHub)
- Filtering: Pre-filter + LLM Ranker
- Explorer: GitHub README, Jina Reader
- Output: One-Pager markdown files
"""

from harness_scraper.models import Article, IntelCard

__version__ = "0.1.0"
__all__ = ["Article", "IntelCard"]
