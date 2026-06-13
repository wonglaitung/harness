"""
Base Source interface for data fetching.

All data sources (RSS, Hacker News, Reddit, etc.) must implement this interface.
"""

from abc import ABC, abstractmethod
from datetime import datetime

from harness_scraper.models import Article


class Source(ABC):
    """
    Abstract base class for data sources.

    A source fetches articles from a specific platform or feed.
    Each source is responsible for:
    1. Fetching incremental articles since a given timestamp
    2. Normalizing to Article format
    3. Handling rate limits and errors
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Source name for logging and identification"""
        pass

    @abstractmethod
    async def fetch(self, since: datetime | None = None) -> list[Article]:
        """
        Fetch articles from this source.

        Args:
            since: Only fetch articles after this timestamp.
                   If None, fetch recent articles (last 24h or source default).

        Returns:
            List of Article objects

        Raises:
            SourceError: On fetch failures
        """
        pass

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup resources"""
        pass


class SourceError(Exception):
    """Error during source fetch operation"""
    pass
