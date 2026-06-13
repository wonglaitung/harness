"""
RSS Source - Fetch articles from RSS/Atom feeds.

Supports:
- Standard RSS 2.0 and Atom feeds
- RSSHub feeds (for X/Twitter lists)
- Auto-discovery of publish dates
"""

import logging
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse

import aiohttp
import feedparser

from harness_scraper.models import Article
from harness_scraper.sources.base import Source, SourceError

logger = logging.getLogger(__name__)


class RSSSource(Source):
    """
    RSS/Atom feed source.

    Fetches articles from RSS feeds including:
    - Official AI blogs (Anthropic, OpenAI, Hugging Face)
    - RSSHub feeds (X/Twitter lists)
    """

    def __init__(self, url: str, name: str | None = None):
        """
        Initialize RSS source.

        Args:
            url: RSS feed URL
            name: Optional display name (defaults to parsed hostname)
        """
        self.url = url
        self._name = name or self._parse_name(url)
        self._session: aiohttp.ClientSession | None = None

    @property
    def name(self) -> str:
        return self._name

    def _parse_name(self, url: str) -> str:
        """Extract name from URL hostname"""
        parsed = urlparse(url)
        hostname = parsed.netloc or parsed.path
        # Remove common prefixes
        hostname = hostname.replace("www.", "").replace("rsshub.app/", "")
        return hostname.split(".")[0].capitalize()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session

    async def fetch(self, since: datetime | None = None) -> list[Article]:
        """
        Fetch articles from RSS feed.

        Args:
            since: Only fetch articles after this timestamp

        Returns:
            List of Article objects
        """
        session = await self._get_session()

        try:
            async with session.get(self.url) as response:
                if response.status != 200:
                    raise SourceError(f"RSS fetch failed: {response.status}")

                content = await response.text()

        except aiohttp.ClientError as e:
            raise SourceError(f"RSS fetch error: {e}") from e

        # Parse feed
        feed = feedparser.parse(content)

        if feed.bozo and not feed.entries:
            raise SourceError(f"RSS parse error: {feed.bozo_exception}")

        # Convert entries to Articles
        articles = []
        for entry in feed.entries:
            article = self._entry_to_article(entry)
            if article:
                # Filter by date if specified
                if since is None or article.published_at >= since:
                    articles.append(article)

        logger.info(f"Fetched {len(articles)} articles from {self.name}")
        return articles

    def _entry_to_article(self, entry: Any) -> Article | None:
        """Convert feed entry to Article"""
        if not entry.get("link"):
            return None

        # Parse publish date
        published_at = datetime.now()
        if entry.get("published_parsed"):
            try:
                published_at = datetime(*entry.published_parsed[:6])
            except (TypeError, ValueError):
                pass
        elif entry.get("updated_parsed"):
            try:
                published_at = datetime(*entry.updated_parsed[:6])
            except (TypeError, ValueError):
                pass

        # Extract content
        content = ""
        if entry.get("summary"):
            content = entry.summary
        elif entry.get("content"):
            content = entry.content[0].get("value", "")

        return Article(
            url=entry.link,
            title=entry.get("title", "Untitled"),
            content=self._clean_content(content),
            source=self.name,
            published_at=published_at,
        )

    def _clean_content(self, content: str) -> str:
        """Clean HTML and truncate content"""
        import re
        # Remove HTML tags
        content = re.sub(r"<[^>]+>", " ", content)
        # Normalize whitespace
        content = re.sub(r"\s+", " ", content).strip()
        # Truncate to 2000 chars
        return content[:2000]

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session and not self._session.closed:
            await self._session.close()


def create_rss_sources(configs: list[dict[str, str]]) -> list[RSSSource]:
    """
    Create RSS sources from config list.

    Args:
        configs: List of {"url": "...", "name": "..."} dicts

    Returns:
        List of RSSSource instances
    """
    return [RSSSource(url=c["url"], name=c.get("name")) for c in configs]
