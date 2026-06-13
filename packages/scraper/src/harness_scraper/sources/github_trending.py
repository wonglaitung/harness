"""
GitHub Trending Source - Fetch trending AI repositories.

GitHub doesn't provide an official API for trending, so we scrape the HTML page.

Supports:
- Filter by language (Python, TypeScript, etc.)
- Filter by since (daily, weekly, monthly)
- Filter by topic keywords
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Any

import aiohttp

from harness_scraper.models import Article
from harness_scraper.sources.base import Source, SourceError

logger = logging.getLogger(__name__)

GITHUB_TRENDING_URL = "https://github.com/trending"

# AI-related languages and topics
AI_LANGUAGES = ["python", "jupyter-notebook", "typescript", "rust"]
AI_KEYWORDS = [
    "ai", "llm", "gpt", "claude", "openai", "anthropic",
    "machine-learning", "deep-learning", "neural-network",
    "transformer", "rag", "agent", "mcp", "langchain",
    "embeddings", "vector", "lora", "fine-tuning",
    "inference", "vllm", "ollama", "llama", "mistral",
    "diffusion", "stable-diffusion", "speech", "vision",
]


class GitHubTrendingSource(Source):
    """
    GitHub Trending source.

    Fetches trending repositories and filters for AI-related projects.
    """

    def __init__(
        self,
        languages: list[str] | None = None,
        since: str = "daily",
        max_repos: int = 25,
        ai_keywords: list[str] | None = None,
    ):
        """
        Initialize GitHub Trending source.

        Args:
            languages: Programming languages to filter (default: AI_LANGUAGES)
            since: Time range - "daily", "weekly", or "monthly"
            max_repos: Maximum repos to fetch per language
            ai_keywords: Keywords to filter AI-related repos
        """
        self.languages = languages or AI_LANGUAGES
        self.since = since
        self.max_repos = max_repos
        self.ai_keywords = ai_keywords or AI_KEYWORDS
        self._session: aiohttp.ClientSession | None = None

    @property
    def name(self) -> str:
        return "GitHub Trending"

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; HarnessScraper/1.0)",
                    "Accept": "text/html",
                },
            )
        return self._session

    async def fetch(self, since: datetime | None = None) -> list[Article]:
        """
        Fetch trending AI repositories.

        Strategy:
        1. Fetch trending page for each language
        2. Parse HTML to extract repo info
        3. Filter for AI-related repos

        Args:
            since: Only fetch repos after this timestamp (not used, trending is always recent)

        Returns:
            List of Article objects
        """
        session = await self._get_session()
        articles = []
        seen_repos: set[str] = set()

        for language in self.languages:
            try:
                repos = await self._fetch_trending_for_language(session, language)
                for repo in repos:
                    if repo["full_name"] in seen_repos:
                        continue
                    if self._is_ai_related(repo):
                        article = self._repo_to_article(repo)
                        if article:
                            articles.append(article)
                            seen_repos.add(repo["full_name"])
            except Exception as e:
                logger.warning(f"Failed to fetch trending for {language}: {e}")

        logger.info(f"Fetched {len(articles)} AI trending repos")
        return articles[:self.max_repos]

    async def _fetch_trending_for_language(
        self, session: aiohttp.ClientSession, language: str
    ) -> list[dict[str, Any]]:
        """Fetch trending repos for a specific language"""
        url = f"{GITHUB_TRENDING_URL}/{language}?since={self.since}"

        async with session.get(url) as resp:
            if resp.status != 200:
                logger.warning(f"GitHub trending returned {resp.status}")
                return []

            html = await resp.text()
            return self._parse_trending_html(html)

    def _parse_trending_html(self, html: str) -> list[dict[str, Any]]:
        """Parse GitHub trending HTML to extract repo info"""
        repos = []

        # Pattern to match repo links: href="/owner/repo" (excluding sponsors, apps, trending, etc.)
        # Use positive lookahead to find repo links followed by description
        article_pattern = r'<article[^>]*class="Box-row"[^>]*>(.*?)</article>'

        for match in re.finditer(article_pattern, html, re.DOTALL):
            article_html = match.group(1)

            # Extract repo link: href="/owner/repo" (not /sponsors/, /apps/, /trending/)
            # Find all href patterns and filter valid repos
            href_pattern = r'href="/([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)"'
            all_hrefs = re.findall(href_pattern, article_html)

            # Filter out non-repo links
            full_name = None
            for href in all_hrefs:
                if not any(href.startswith(prefix) for prefix in ["sponsors/", "apps/", "trending/", "login", "site/"]):
                    full_name = href
                    break

            if not full_name:
                continue

            # Extract description - look for <p class="col-9...
            desc_match = re.search(r'<p[^>]*class="col-9[^"]*"[^>]*>(.*?)</p>', article_html, re.DOTALL)
            description = ""
            if desc_match:
                description = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()

            # Extract language
            lang_match = re.search(r'<span[^>]*itemprop="programmingLanguage"[^>]*>([^<]+)</span>', article_html)
            language = lang_match.group(1).strip() if lang_match else ""

            # Extract stars gained today
            stars_match = re.search(r'([0-9,]+)\s*stars?\s*today', article_html, re.IGNORECASE)
            stars_today = 0
            if stars_match:
                stars_today = int(stars_match.group(1).replace(",", ""))

            repos.append({
                "full_name": full_name,
                "description": description,
                "language": language,
                "stars_today": stars_today,
                "url": f"https://github.com/{full_name}",
            })

        return repos

    def _is_ai_related(self, repo: dict[str, Any]) -> bool:
        """Check if a repo is AI-related"""
        text_to_check = (
            repo.get("description", "").lower() + " " +
            repo.get("full_name", "").lower()
        )

        for keyword in self.ai_keywords:
            if keyword.lower() in text_to_check:
                return True

        return False

    def _repo_to_article(self, repo: dict[str, Any]) -> Article:
        """Convert GitHub repo to Article"""
        full_name = repo["full_name"]
        description = repo.get("description", "")
        stars_today = repo.get("stars_today", 0)

        # Build content
        content = f"""Repository: {full_name}
Description: {description}
Language: {repo.get('language', 'Unknown')}
Stars today: {stars_today}
URL: {repo['url']}
"""
        # Title format: "owner/repo - description (if short)" or just "owner/repo"
        title = full_name
        if description and len(description) < 80:
            title = f"{full_name} - {description}"

        return Article(
            url=repo["url"],
            title=title,
            content=content,
            source="GitHub Trending",
            published_at=datetime.now(),
            score=stars_today,  # Use stars today as "score"
            github_urls=[repo["url"]],
        )

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session and not self._session.closed:
            await self._session.close()
