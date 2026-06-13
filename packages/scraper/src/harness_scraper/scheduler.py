"""
Scheduler - Orchestrate the scraping pipeline.

Pipeline:
1. Fetch articles from all sources
2. Pre-filter
3. LLM Rank
4. Explore (GitHub README)
5. Generate One-Pager
6. Save to file system
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

from harness_scraper.config import load_config
from harness_scraper.explorer import GitHubExplorer, JinaReaderExplorer
from harness_scraper.filters import LLMRanker, PreFilter
from harness_scraper.llm import LLMClient
from harness_scraper.models import Article, ScraperConfig
from harness_scraper.output import DedupStore, OnePagerGenerator
from harness_scraper.sources import Source
from harness_scraper.sources.hacker_news import HackerNewsSource
from harness_scraper.sources.rss import create_rss_sources

logger = logging.getLogger(__name__)


class ScraperScheduler:
    """
    Scraper scheduler - runs the full pipeline.

    Usage:
        scheduler = ScraperScheduler(config)
        await scheduler.run_once()  # Single run
        await scheduler.run()       # Continuous with interval
    """

    def __init__(self, config: ScraperConfig | None = None):
        """
        Initialize scheduler.

        Args:
            config: Scraper configuration (loads from file if None)
        """
        self.config = config or load_config()
        self.llm_client = LLMClient(self.config.llm)
        self.prefilter = PreFilter(self.config.filter)
        self.ranker = LLMRanker(self.llm_client)
        self.one_pager_gen = OnePagerGenerator(self.llm_client)
        self.dedup = DedupStore(self.config.output.dedup_db)
        self.github_explorer = GitHubExplorer()
        self.jina_explorer = JinaReaderExplorer()

    def _create_sources(self) -> list[Source]:
        """Create data sources from config"""
        sources: list[Source] = []

        # RSS sources
        if self.config.sources.rss:
            sources.extend(create_rss_sources(self.config.sources.rss))

        # Hacker News source
        hn_config = self.config.sources.hacker_news
        sources.append(
            HackerNewsSource(
                min_points=hn_config.get("min_points", 150),
                include_show_hn=hn_config.get("include_show_hn", True),
            )
        )

        return sources

    async def run_once(self, since: datetime | None = None):
        """
        Run the pipeline once.

        Args:
            since: Only fetch articles after this timestamp
        """
        if since is None:
            since = datetime.now() - timedelta(hours=12)

        logger.info(f"Starting scraper run since {since}")

        # Phase 1: Fetch from all sources
        all_articles: list[Article] = []
        for source in self._create_sources():
            try:
                async with source:
                    articles = await source.fetch(since=since)
                    all_articles.extend(articles)
            except Exception as e:
                logger.error(f"Source {source.name} failed: {e}")

        logger.info(f"Fetched {len(all_articles)} total articles")

        # Phase 2: Pre-filter
        filtered = self.prefilter.filter_batch(all_articles)

        # Phase 3: Dedup
        new_articles = [a for a in filtered if not self.dedup.is_seen(a.url)]
        logger.info(f"{len(new_articles)} new articles after dedup")

        # Phase 4: LLM Rank
        ranked = await self.ranker.rank_batch(new_articles)
        passed = [(a, j) for a, j in ranked if j.is_new_paradigm]

        # Phase 5: Explore and Generate One-Pager
        output_dir = Path(self.config.output.directory).expanduser()
        date_dir = output_dir / datetime.now().strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)

        for article, judgment in passed:
            try:
                # Get README content
                readme = None

                # Try GitHub first
                if article.github_urls:
                    readme = await self.github_explorer.fetch_readme(article.github_urls[0])
                elif "github.com" in article.url:
                    readme = await self.github_explorer.fetch_readme(article.url)

                # Fallback to Jina Reader
                if not readme:
                    readme = await self.jina_explorer.fetch(article.url)

                if not readme:
                    logger.warning(f"No content found for {article.title[:50]}...")
                    continue

                # Generate One-Pager
                card = await self.one_pager_gen.generate(article, readme)
                if not card:
                    continue

                # Save to file
                filename = self.one_pager_gen.to_filename(card)
                filepath = date_dir / filename
                markdown = self.one_pager_gen.to_markdown(card)

                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(markdown)

                logger.info(f"Saved: {filepath}")

                # Mark as seen
                self.dedup.mark_seen(article.url, card.concept_name)

            except Exception as e:
                logger.error(f"Failed to process {article.title[:50]}...: {e}")

        logger.info(f"Run complete. Generated {len(passed)} one-pagers")

    async def run(self, interval_hours: int = 12):
        """
        Run continuously at interval.

        Args:
            interval_hours: Hours between runs
        """
        while True:
            try:
                await self.run_once()
            except Exception as e:
                logger.error(f"Run failed: {e}")

            logger.info(f"Sleeping for {interval_hours} hours...")
            await asyncio.sleep(interval_hours * 3600)

    async def close(self):
        """Cleanup resources"""
        await self.llm_client.close()
        await self.github_explorer.close()
        await self.jina_explorer.close()
        self.dedup.close()