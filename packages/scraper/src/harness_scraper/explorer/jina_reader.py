"""
Jina Reader Explorer - Fetch content using Jina Reader API.

Jina Reader converts any URL to clean Markdown.
Useful for:
- Non-GitHub URLs (Hugging Face, blogs, etc.)
- Fallback when GitHub fetch fails
- Documentation pages

API: https://r.jina.ai/{url}
"""

import logging
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

JINA_READER_BASE = "https://r.jina.ai"


class JinaReaderExplorer:
    """
    Jina Reader API wrapper.

    Fetches and converts web content to clean Markdown.
    Free to use, no API key required.
    """

    def __init__(self):
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=60),
                headers={"Accept": "text/markdown"},
            )
        return self._session

    async def fetch(self, url: str) -> Optional[str]:
        """
        Fetch content from URL using Jina Reader.

        Args:
            url: Any URL to fetch and convert

        Returns:
            Markdown content or None on failure
        """
        session = await self._get_session()
        reader_url = f"{JINA_READER_BASE}/{url}"

        try:
            async with session.get(reader_url) as resp:
                if resp.status == 200:
                    content = await resp.text()
                    logger.info(f"Jina Reader fetched: {url[:50]}...")
                    return self._clean_content(content)
                else:
                    logger.warning(f"Jina Reader error: {resp.status}")
                    return None

        except aiohttp.ClientError as e:
            logger.error(f"Jina Reader fetch error: {e}")
            return None

    def _clean_content(self, content: str) -> str:
        """Clean content"""
        # Truncate to reasonable length
        return content[:10000]

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()