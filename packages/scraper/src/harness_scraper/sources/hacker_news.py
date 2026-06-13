"""
Hacker News Source - Fetch high-quality posts from HN.

Supports:
- Top stories with minimum points threshold
- Show HN posts
- New stories
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import aiohttp

from harness_scraper.models import Article
from harness_scraper.sources.base import Source, SourceError

logger = logging.getLogger(__name__)

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"


class ShowHNSource(Source):
    """
    Show HN 专门源 - 降低阈值捕获早期新项目。

    很多改变范式的 Harness 工具在刚 Show HN 时分数并不高，
    需要单独源以更低阈值（50）来捕获。
    """

    def __init__(
        self,
        min_points: int = 50,
        max_stories: int = 100,
    ):
        """
        Initialize Show HN source.

        Args:
            min_points: Minimum points threshold (default 50, lower than regular HN)
            max_stories: Maximum stories to fetch
        """
        self.min_points = min_points
        self.max_stories = max_stories
        self._session: aiohttp.ClientSession | None = None

    @property
    def name(self) -> str:
        return "Show HN"

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session

    async def fetch(self, since: datetime | None = None) -> list[Article]:
        """Fetch Show HN posts with lower points threshold."""
        session = await self._get_session()
        articles = []

        # Only fetch showstories (Show HN)
        async with session.get(f"{HN_API_BASE}/showstories.json") as resp:
            if resp.status != 200:
                logger.warning(f"Show HN fetch failed: {resp.status}")
                return []
            story_ids = await resp.json()

        # Fetch story details
        for i, story_id in enumerate(story_ids[:self.max_stories]):
            if i > 0 and i % 10 == 0:
                logger.info(f"Fetched {i}/{len(story_ids[:self.max_stories])} Show HN posts")

            try:
                async with session.get(f"{HN_API_BASE}/item/{story_id}.json") as resp:
                    if resp.status == 200:
                        story = await resp.json()
                        if story:
                            article = self._story_to_article(story)
                            if article and article.score >= self.min_points:
                                articles.append(article)
            except Exception as e:
                logger.warning(f"Failed to fetch Show HN story {story_id}: {e}")

        logger.info(f"Fetched {len(articles)} Show HN posts with score >= {self.min_points}")
        return articles

    def _story_to_article(self, story: dict[str, Any]) -> Article | None:
        """Convert HN story to Article"""
        if not story.get("url") or not story.get("title"):
            # Show HN often has text-only posts without URL
            hn_url = f"https://news.ycombinator.com/item?id={story.get('id')}"
            title = story.get("title", "Untitled")
            if not title.startswith("Show HN"):
                return None

        published_at = datetime.now()
        if story.get("time"):
            published_at = datetime.fromtimestamp(story["time"])

        content = story.get("text", "")
        url = story.get("url", f"https://news.ycombinator.com/item?id={story['id']}")

        if story.get("url"):
            content = f"URL: {story['url']}\n\n{content}"

        return Article(
            url=url,
            title=story.get("title", "Untitled"),
            content=content[:2000],
            source="Show HN",
            published_at=published_at,
            score=story.get("score", 0),
        )

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session and not self._session.closed:
            await self._session.close()


class HackerNewsSource(Source):
    """
    Hacker News source.

    Fetches posts based on:
    - Minimum points threshold
    - Optional Show HN filter
    """

    def __init__(
        self,
        min_points: int = 150,
        include_show_hn: bool = True,
        max_stories: int = 100,
    ):
        """
        Initialize HN source.

        Args:
            min_points: Minimum points threshold
            include_show_hn: Include Show HN posts
            max_stories: Maximum stories to fetch per run
        """
        self.min_points = min_points
        self.include_show_hn = include_show_hn
        self.max_stories = max_stories
        self._session: aiohttp.ClientSession | None = None

    @property
    def name(self) -> str:
        return "Hacker News"

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session

    async def fetch(self, since: datetime | None = None) -> list[Article]:
        """
        Fetch high-quality HN posts.

        Strategy:
        1. Fetch top story IDs
        2. If include_show_hn, fetch show story IDs
        3. Fetch story details
        4. Filter by points and date

        Args:
            since: Only fetch stories after this timestamp

        Returns:
            List of Article objects
        """
        session = await self._get_session()
        articles = []

        # Fetch story IDs
        story_ids = await self._fetch_story_ids(session)

        # Fetch story details (with rate limiting)
        for i, story_id in enumerate(story_ids[: self.max_stories]):
            if i > 0 and i % 10 == 0:
                logger.info(f"Fetched {i}/{len(story_ids[:self.max_stories])} stories")

            try:
                story = await self._fetch_story(session, story_id)
                if story:
                    article = self._story_to_article(story)
                    if article and article.score >= self.min_points:
                        if since is None or article.published_at >= since:
                            articles.append(article)
            except Exception as e:
                logger.warning(f"Failed to fetch story {story_id}: {e}")

        logger.info(f"Fetched {len(articles)} HN posts with score >= {self.min_points}")
        return articles

    async def _fetch_story_ids(self, session: aiohttp.ClientSession) -> list[int]:
        """Fetch story IDs from HN API"""
        story_ids = []

        # Top stories
        async with session.get(f"{HN_API_BASE}/topstories.json") as resp:
            if resp.status == 200:
                story_ids.extend(await resp.json())

        # Show HN stories
        if self.include_show_hn:
            async with session.get(f"{HN_API_BASE}/showstories.json") as resp:
                if resp.status == 200:
                    story_ids.extend(await resp.json())

        return list(set(story_ids))

    async def _fetch_story(
        self, session: aiohttp.ClientSession, story_id: int
    ) -> dict[str, Any] | None:
        """Fetch single story details"""
        async with session.get(f"{HN_API_BASE}/item/{story_id}.json") as resp:
            if resp.status == 200:
                return await resp.json()
        return None

    def _story_to_article(self, story: dict[str, Any]) -> Article | None:
        """Convert HN story to Article"""
        if not story.get("url") or not story.get("title"):
            return None

        # Parse timestamp
        published_at = datetime.now()
        if story.get("time"):
            published_at = datetime.fromtimestamp(story["time"])

        # Build content
        content = story.get("text", "")
        if story.get("url"):
            content = f"URL: {story['url']}\n\n{content}"

        return Article(
            url=story.get("url", f"https://news.ycombinator.com/item?id={story['id']}"),
            title=story.get("title", "Untitled"),
            content=content[:2000],
            source="Hacker News",
            published_at=published_at,
            score=story.get("score", 0),
        )

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session and not self._session.closed:
            await self._session.close()
