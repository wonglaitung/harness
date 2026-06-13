"""
Pre-filter - Quick keyword-based filtering.

Purpose:
- Quickly filter out obviously irrelevant articles
- Pass through high-score HN posts
- Reduce load on LLM Ranker
"""

import logging
import re
from typing import Any

from harness_scraper.models import Article, FilterConfig

logger = logging.getLogger(__name__)


class PreFilter:
    """
    Pre-filter for quick article filtering.

    Strategy:
    1. High-score HN posts (> threshold) pass through directly
    2. Check for keywords in title/content
    3. Check for GitHub URLs
    """

    def __init__(self, config: FilterConfig | None = None):
        """
        Initialize pre-filter.

        Args:
            config: Filter configuration
        """
        self.config = config or FilterConfig()
        self.keywords = [kw.lower() for kw in self.config.prefilter_keywords]
        # Compile patterns for installation commands
        self._install_patterns = [
            re.compile(r"npm\s+install", re.IGNORECASE),
            re.compile(r"pip\s+install", re.IGNORECASE),
            re.compile(r"docker\s+run", re.IGNORECASE),
            re.compile(r"cargo\s+install", re.IGNORECASE),
            re.compile(r"go\s+install", re.IGNORECASE),
            re.compile(r"brew\s+install", re.IGNORECASE),
        ]

    def should_process(self, article: Article) -> bool:
        """
        Check if article should proceed to LLM Ranker.

        Args:
            article: Article to check

        Returns:
            True if article should be processed further
        """
        # High-score HN posts bypass prefilter
        if article.score >= self.config.hn_high_score_threshold:
            logger.debug(f"High-score bypass: {article.title[:50]}... (score={article.score})")
            return True

        # Check for GitHub URLs
        if "github.com" in article.url.lower():
            logger.debug(f"GitHub URL found: {article.url}")
            return True

        # Check content
        content_lower = (article.title + " " + article.content).lower()

        # Check keywords
        for keyword in self.keywords:
            if keyword in content_lower:
                logger.debug(f"Keyword match '{keyword}': {article.title[:50]}...")
                return True

        # Check installation patterns
        for pattern in self._install_patterns:
            if pattern.search(article.content):
                logger.debug(f"Install command found: {article.title[:50]}...")
                return True

        return False

    def filter_batch(self, articles: list[Article]) -> list[Article]:
        """
        Filter a batch of articles.

        Args:
            articles: List of articles

        Returns:
            Filtered list of articles
        """
        passed = [a for a in articles if self.should_process(a)]
        logger.info(f"Pre-filter: {len(passed)}/{len(articles)} articles passed")
        return passed
