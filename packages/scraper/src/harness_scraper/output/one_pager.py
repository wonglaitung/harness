"""
One-Pager Generator - Generate structured intelligence cards from README.

Uses LLM to extract structured information from README content.
"""

import json
import logging
from datetime import datetime

from harness_scraper.llm import LLMClient
from harness_scraper.models import Article, IntelCard

logger = logging.getLogger(__name__)


class OnePagerGenerator:
    """
    One-Pager generator using LLM.

    Extracts structured intelligence from README content:
    - Concept name
    - Technical definition
    - Pain point
    - Old vs new paradigm
    - Production impact
    - Adoption cost
    """

    EXTRACT_PROMPT = """基于以下 GitHub README 内容，提取技术情报。

README 内容：
{readme_content}

要求：
1. 无论输入的 README 为何种语言，请一律使用中文进行结构化情报的填充
2. 用大白话解释技术概念，避免专业术语堆砌
3. 请严格按以下 JSON 格式输出，不要添加任何其他文字：
{{
    "concept_name": "名称",
    "definition": "技术定义（用大白话解释）",
    "pain_point": "解决的痛点",
    "old_paradigm": "旧做法",
    "new_paradigm": "新做法",
    "production_impact": "生产力影响",
    "adoption_cost": "采用成本评估"
}}"""

    def __init__(self, llm_client: LLMClient):
        """
        Initialize One-Pager generator.

        Args:
            llm_client: LLM client instance
        """
        self.llm = llm_client

    async def generate(
        self,
        article: Article,
        readme: str,
    ) -> IntelCard | None:
        """
        Generate IntelCard from README content.

        Args:
            article: Source article
            readme: README content

        Returns:
            IntelCard or None on failure
        """
        prompt = self.EXTRACT_PROMPT.format(readme_content=readme[:8000])

        try:
            response = await self.llm.generate(
                prompt=prompt,
                json_mode=True,
            )

            data = json.loads(response)

            # Extract GitHub URL
            github_url = ""
            if article.github_urls:
                github_url = article.github_urls[0]
            elif "github.com" in article.url:
                github_url = article.url

            return IntelCard(
                concept_name=data.get("concept_name", article.title),
                definition=data.get("definition", ""),
                pain_point=data.get("pain_point", ""),
                old_paradigm=data.get("old_paradigm", ""),
                new_paradigm=data.get("new_paradigm", ""),
                production_impact=data.get("production_impact", ""),
                adoption_cost=data.get("adoption_cost", ""),
                github_url=github_url,
                hn_url=article.url if "news.ycombinator.com" in article.url else "",
                published_at=article.published_at,
                source_url=article.url,
            )

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"One-pager generation error: {e}")
            return None

    def to_markdown(self, card: IntelCard) -> str:
        """
        Convert IntelCard to Markdown string.

        Args:
            card: IntelCard to convert

        Returns:
            Markdown string
        """
        return card.to_markdown()

    def to_filename(self, card: IntelCard) -> str:
        """
        Generate filename from concept name.

        Args:
            card: IntelCard

        Returns:
            Safe filename string
        """
        import re
        # Convert to lowercase, replace spaces with hyphens
        name = card.concept_name.lower()
        name = re.sub(r"[^\w\s-]", "", name)
        name = re.sub(r"[\s_]+", "-", name)
        name = re.sub(r"-+", "-", name).strip("-")
        return f"{name}.md"
