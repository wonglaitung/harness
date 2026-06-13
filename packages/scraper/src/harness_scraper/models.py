"""
Pydantic data models for structured data.

Key models:
- Article: Raw article from sources (RSS, HN, Reddit)
- IntelCard: LLM-extracted structured intelligence
- Judgment: LLM ranker's classification result
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class Article(BaseModel):
    """
    原始文章 - 从数据源抓取的文章。

    Attributes:
        url: 文章链接
        title: 文章标题
        content: 文章摘要/内容
        source: 来源名称 (Anthropic Blog, Hacker News, etc.)
        published_at: 发布时间
        score: 置信度/热度 (HN points, Reddit upvotes)
        github_urls: 文章中包含的 GitHub 链接列表
    """

    url: str = Field(description="文章链接")
    title: str = Field(description="文章标题")
    content: str = Field(description="文章摘要或正文", default="")
    source: str = Field(description="来源名称")
    published_at: datetime = Field(description="发布时间", default_factory=datetime.now)
    score: int = Field(description="热度/置信度", default=0)
    github_urls: list[str] = Field(description="GitHub 链接列表", default_factory=list)

    def extract_github_urls(self) -> list[str]:
        """从内容中提取 GitHub URL"""
        import re
        pattern = r"https?://github\.com/[\w\-]+/[\w\-]+"
        matches = re.findall(pattern, self.content + " " + self.url)
        return list(set(matches))


class Judgment(BaseModel):
    """
    LLM 裁判结果 - 结构化输出。

    Attributes:
        is_new_paradigm: 是否为新范式/工具/标准
        reason: 判断理由
    """

    is_new_paradigm: bool = Field(description="是否定义了新的软件工程范式、工具或标准")
    reason: str = Field(description="简短判断理由", default="")


class IntelCard(BaseModel):
    """
    情报卡片 - LLM 从 README 抽取的结构化信息。

    用于生成 One-Pager Markdown 文件。

    Attributes:
        concept_name: 新概念/工具的官方名称
        definition: 技术定义 (大白话解释)
        pain_point: 解决的痛点
        old_paradigm: 旧做法
        new_paradigm: 新做法
        production_impact: 生产力影响
        adoption_cost: 采用成本评估
        github_url: 官方 GitHub 链接
        hn_url: Hacker News 讨论链接
        published_at: 发布时间
        source_url: 原始文章链接
    """

    concept_name: str = Field(description="新概念或新工具的官方名称")
    definition: str = Field(description="技术定义 - 用大白话解释其本质")
    pain_point: str = Field(description="它刚出现是为了解决什么痛点")
    old_paradigm: str = Field(description="旧做法是什么")
    new_paradigm: str = Field(description="新做法是什么")
    production_impact: str = Field(description="对应用层工作者的实际生产力影响")
    adoption_cost: str = Field(description="采用成本评估 (开发成本、算力成本)")
    github_url: str = Field(description="官方 GitHub 链接", default="")
    hn_url: str = Field(description="HN 讨论链接", default="")
    published_at: datetime = Field(description="发布时间", default_factory=datetime.now)
    source_url: str = Field(description="原始文章链接", default="")

    def to_markdown(self) -> str:
        """转换为 One-Pager Markdown 格式"""
        date_str = self.published_at.strftime("%Y-%m-%d")
        return f"""# {self.concept_name}

## 技术定义 (What)
{self.definition}

## 行业痛点 (Why)
{self.pain_point}

## 旧范式 vs 新范式
- **旧做法**：{self.old_paradigm}
- **新做法**：{self.new_paradigm}

## 生产力影响 (How)
{self.production_impact}

## 采用成本
{self.adoption_cost}

## 核心线索
- GitHub：{self.github_url}
- HN 讨论：{self.hn_url}
- 来源：{self.source_url}
- 发布时间：{date_str}
"""


class LLMConfig(BaseModel):
    """
    LLM 配置 - 支持本地/云端多种提供者。

    Examples:
        # 本地 vLLM
        LLMConfig(provider="vllm", base_url="http://localhost:8000/v1", model="Qwen2.5-7B-Instruct")

        # 硅基流动
        LLMConfig(provider="openai", base_url="https://api.siliconflow.cn/v1", api_key="sk-xxx", model="Qwen/Qwen2.5-7B-Instruct")

        # DeepSeek
        LLMConfig(provider="openai", base_url="https://api.deepseek.com/v1", api_key="sk-xxx", model="deepseek-chat")

        # OpenAI
        LLMConfig(provider="openai", base_url="https://api.openai.com/v1", api_key="sk-xxx", model="gpt-4o-mini")
    """

    provider: str = Field(description="提供者: vllm, ollama, openai, anthropic", default="openai")
    base_url: str = Field(description="API 基础 URL", default="https://api.openai.com/v1")
    api_key: Optional[str] = Field(description="API Key (本地模型可空)", default=None)
    model: str = Field(description="模型名称", default="gpt-4o-mini")
    temperature: float = Field(description="生成温度", default=0.1)
    max_tokens: int = Field(description="最大输出 token", default=1000)


class SourceConfig(BaseModel):
    """数据源配置"""

    rss: list[dict[str, str]] = Field(description="RSS 源列表", default_factory=list)
    hacker_news: dict[str, Any] = Field(description="HN 配置", default_factory=lambda: {"min_points": 150, "include_show_hn": True})
    reddit: dict[str, Any] = Field(description="Reddit 配置", default_factory=lambda: {"subreddits": ["LocalLLaMA"], "timeframe": "24h"})
    github_trending: dict[str, Any] = Field(
        description="GitHub Trending 配置",
        default_factory=lambda: {"enabled": True, "since": "daily", "languages": ["python", "typescript"]}
    )
    show_hn: dict[str, Any] = Field(
        description="Show HN 专门源配置（低阈值捕获早期新项目）",
        default_factory=lambda: {"enabled": True, "min_points": 50}
    )


class FilterConfig(BaseModel):
    """过滤配置"""

    prefilter_keywords: list[str] = Field(
        description="粗筛关键词",
        default_factory=lambda: ["github.com", "release", "announce", "open source", "npm install", "pip install", "docker run"]
    )
    hn_high_score_threshold: int = Field(description="HN 高分阈值，超过则跳过粗筛", default=300)


class OutputConfig(BaseModel):
    """输出配置"""

    directory: str = Field(description="输出目录", default="~/.harness/scraper")
    dedup_db: str = Field(description="增量排重数据库路径", default="~/.harness/scraper/seen.db")


class ScraperConfig(BaseModel):
    """完整配置"""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    sources: SourceConfig = Field(default_factory=SourceConfig)
    filter: FilterConfig = Field(default_factory=FilterConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)