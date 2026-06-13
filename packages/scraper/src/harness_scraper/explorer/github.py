"""
GitHub Explorer - Fetch README from GitHub repositories.

Features:
- Multiple README filename attempts
- Raw content fetching
- Rate limit handling
"""

import logging
import re
from urllib.parse import urlparse

import aiohttp

logger = logging.getLogger(__name__)

# README filename alternatives (in priority order)
README_NAMES = [
    "README.md",
    "README.rst",
    "README.txt",
    "readme.md",
    "README",
    "docs/index.md",
]


class GitHubExplorer:
    """
    GitHub README fetcher.

    Fetches README content from GitHub repositories using raw URLs.
    Handles rate limits and multiple README filename variations.
    """

    RATE_LIMIT_DELAY = 1.0  # Delay between requests to avoid rate limit

    def __init__(self):
        self._session: aiohttp.ClientSession | None = None
        self._last_request_time: float = 0

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"Accept": "text/plain"},
            )
        return self._session

    def parse_github_url(self, url: str) -> tuple[str, str] | None:
        """
        Parse GitHub URL to extract owner and repo.

        Handles:
        - https://github.com/owner/repo
        - https://github.com/owner/repo.git
        - github.com/owner/repo

        Returns:
            (owner, repo) tuple or None if invalid
        """
        # Normalize URL
        url = url.strip()
        if not url.startswith("http"):
            url = "https://" + url

        # Remove trailing .git
        url = url.rstrip(".git")

        # Parse
        pattern = r"https?://github\.com/([\w\-]+)/([\w\-]+)"
        match = re.match(pattern, url)

        if match:
            return match.group(1), match.group(2)
        return None

    async def fetch_readme(self, github_url: str) -> str | None:
        """
        Fetch README content from GitHub repository.

        Tries multiple README filenames until one succeeds.

        Args:
            github_url: GitHub repository URL

        Returns:
            README content or None if not found
        """
        parsed = self.parse_github_url(github_url)
        if not parsed:
            logger.warning(f"Invalid GitHub URL: {github_url}")
            return None

        owner, repo = parsed
        session = await self._get_session()

        # Try multiple README names
        for readme_name in README_NAMES:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{readme_name}"
            # Also try master branch
            master_url = f"https://raw.githubusercontent.com/{owner}/{repo}/master/{readme_name}"

            for url in [raw_url, master_url]:
                try:
                    content = await self._fetch_with_rate_limit(session, url)
                    if content:
                        logger.info(f"Found README: {readme_name} ({url})")
                        return self._clean_readme(content)

                except aiohttp.ClientError as e:
                    logger.debug(f"Failed to fetch {url}: {e}")

        logger.warning(f"No README found for {github_url}")
        return None

    async def _fetch_with_rate_limit(
        self, session: aiohttp.ClientSession, url: str
    ) -> str | None:
        """Fetch with rate limit delay"""
        import asyncio
        import time

        elapsed = time.time() - self._last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            await asyncio.sleep(self.RATE_LIMIT_DELAY - elapsed)

        self._last_request_time = time.time()

        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.text()
            elif resp.status == 404:
                return None
            elif resp.status == 403:
                logger.warning("GitHub rate limit hit")
                await asyncio.sleep(60)  # Wait before retry
                return None
            else:
                logger.warning(f"GitHub fetch error: {resp.status}")
                return None

    def _clean_readme(self, content: str) -> str:
        """Clean README content"""
        # Remove excessive whitespace
        content = re.sub(r"\n{3,}", "\n\n", content)
        # Truncate to reasonable length
        return content[:10000]

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()