"""
LLM Client - Unified interface for local and cloud LLMs.

Supports:
- Local vLLM / Ollama
- OpenAI-compatible APIs (SiliconFlow, DeepSeek, etc.)
- OpenAI official API

Features:
- Global session reuse
- Concurrency control (Semaphore)
- JSON mode for structured output
"""

import asyncio
import logging
from typing import Optional

import aiohttp

from harness_scraper.models import LLMConfig

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Unified LLM client with concurrency control.

    Supports all OpenAI-compatible APIs:
    - vLLM: http://localhost:8000/v1
    - Ollama: http://localhost:11434/v1
    - SiliconFlow: https://api.siliconflow.cn/v1
    - DeepSeek: https://api.deepseek.com/v1
    - OpenAI: https://api.openai.com/v1
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.headers = {}
        if config.api_key:
            self.headers["Authorization"] = f"Bearer {config.api_key}"

        self._session: Optional[aiohttp.ClientSession] = None
        # Concurrency control - protect local vLLM/Ollama from OOM
        self._semaphore = asyncio.Semaphore(2)

    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create global session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=60),
            )
        return self._session

    async def generate(
        self,
        prompt: str,
        system: str = "",
        json_mode: bool = False,
    ) -> str:
        """
        Generate completion from LLM.

        Args:
            prompt: User prompt
            system: System prompt (optional)
            json_mode: Force JSON output

        Returns:
            Generated text
        """
        session = await self.get_session()

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with self._semaphore:  # Concurrency protection
            try:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"LLM API error {resp.status}: {error_text}")
                        return "{}" if json_mode else ""

                    result = await resp.json()
                    return result["choices"][0]["message"]["content"]

            except asyncio.TimeoutError:
                logger.error("LLM API timeout")
                return "{}" if json_mode else ""
            except Exception as e:
                logger.error(f"LLM generation error: {e}")
                return "{}" if json_mode else ""

    async def close(self):
        """Close session"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
