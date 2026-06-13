"""
LLM Ranker - Judge articles using LLM.

Purpose:
- Determine if article defines a new paradigm/tool/standard
- Use structured JSON output for reliable parsing
- Fallback to keyword matching on failure
"""

import json
import logging
from typing import Any

from harness_scraper.llm import LLMClient
from harness_scraper.models import Article, Judgment

logger = logging.getLogger(__name__)


class LLMRanker:
    """
    LLM-based article ranker.

    Uses local or cloud LLM to judge if an article:
    1. Defines a new software engineering paradigm
    2. Introduces a new tool or library
    3. Proposes a new standard or protocol
    """

    SYSTEM_PROMPT = """你是一个前沿技术专家，负责筛选具有范式转变（Paradigm Shift）或创新性的 AI 开源项目与技术。

你的任务是判断文章是否：
1. 定义了新的软件工程范式
2. 引入了新的工具或库
3. 提出了新的标准或协议

不要通过已有技术的文章（如教程、最佳实践），只标记真正有创新性的内容。"""

    USER_PROMPT = """请评估以下技术文章是否代表了新工具、新范式或重大技术突破。

标题：{title}
摘要：{content}

请严格按 JSON 格式返回，不要添加任何其他文字：
{{"is_new_paradigm": true, "reason": "简短理由"}}
或
{{"is_new_paradigm": false, "reason": "简短理由"}}"""

    def __init__(self, llm_client: LLMClient):
        """
        Initialize LLM ranker.

        Args:
            llm_client: LLM client instance
        """
        self.llm = llm_client

    async def rank(self, article: Article) -> Judgment:
        """
        Judge if article represents new paradigm.

        Args:
            article: Article to judge

        Returns:
            Judgment with is_new_paradigm flag and reason
        """
        prompt = self.USER_PROMPT.format(
            title=article.title,
            content=article.content[:1500]  # Truncate for token limit
        )

        try:
            response = await self.llm.generate(
                prompt=prompt,
                system=self.SYSTEM_PROMPT,
                json_mode=True,
            )

            # Parse JSON response
            data = json.loads(response)
            return Judgment(
                is_new_paradigm=data.get("is_new_paradigm", False),
                reason=data.get("reason", ""),
            )

        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error: {e}, response: {response[:200]}")
            # Fallback: keyword matching
            return self._fallback_judgment(article, response)

        except Exception as e:
            logger.error(f"LLM rank error: {e}")
            return Judgment(is_new_paradigm=False, reason=f"Error: {e}")

    def _fallback_judgment(self, article: Article, response: str) -> Judgment:
        """Fallback judgment when JSON parsing fails"""
        response_upper = response.upper()
        is_yes = any(kw in response_upper for kw in ["YES", "TRUE", "是", "新范式"])

        return Judgment(
            is_new_paradigm=is_yes,
            reason="Fallback: keyword matching",
        )

    async def rank_batch(self, articles: list[Article]) -> list[tuple[Article, Judgment]]:
        """
        Rank a batch of articles.

        Args:
            articles: List of articles

        Returns:
            List of (article, judgment) tuples
        """
        results = []
        for article in articles:
            judgment = await self.rank(article)
            results.append((article, judgment))

            if judgment.is_new_paradigm:
                logger.info(f"New paradigm found: {article.title[:50]}...")

        passed = sum(1 for _, j in results if j.is_new_paradigm)
        logger.info(f"LLM Ranker: {passed}/{len(articles)} articles passed")
        return results
