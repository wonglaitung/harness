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

    SYSTEM_PROMPT = """你是一个技术雷达裁判，负责识别 AI 行业中的新前沿线索。

你的任务是判断文章是否包含以下任意一类"新前沿线索"：

**应该标记为 TRUE 的情况**：
1. **新技术范式或行业黑话**：社区自发形成的新概念（如 taste-skill、vibe-coding、prompt-engineering）
2. **新开源模型微调流派**：新的微调方法、模型架构（如 Hermes 系列、Agent 运行时）
3. **新评测/脚手架工具**：自动化评测框架、MCP 服务、各种 Harness（如 evaluation harness）
4. **新协议或标准**：MCP、GGUF、新的 Agent 通信协议
5. **刚发布的新项目**（< 3个月）且具有范式转变意义

**必须标记为 FALSE 的情况**：
1. **成熟项目**：已存在超过 3个月的知名项目（vLLM、LangChain、Ollama、LlamaIndex）
2. **纯教程/最佳实践**：不包含新概念，只是现有技术的使用指南
3. **增量更新**：版本升级、bug 修复、性能优化
4. **纯应用实现**：用现有技术做某个具体应用（如"AI 写邮件助手"）

**判断依据**：
- 项目热度高不代表是新范式
- 注意识别"黑话"词汇（taste-skill、harness、hermes 等），这类词汇的出现往往意味着新概念
- 独立开发者/前端类的审美概念也属于新范式范畴"""

    USER_PROMPT = """请评估以下技术内容是否包含"新前沿线索"。

标题：{title}
摘要：{content}

判断标准：
- TRUE: 新范式/黑话（taste-skill、vibe-coding）、新微调流派（Hermes）、新评测工具（Harness）、新协议（MCP）
- FALSE: 成熟项目（vLLM、LangChain）、纯教程、增量更新、纯应用实现

请严格按 JSON 格式返回：
{{"is_new_paradigm": false, "reason": "为何不符合"}}
或
{{"is_new_paradigm": true, "reason": "新范式是什么", "keywords": ["识别到的核心新词"]}}"""

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
