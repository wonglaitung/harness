"""
Pydantic data models for scraper configuration.

The intelligence extraction is now handled by the SDK Agent,
so we only need configuration models here.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


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
    max_tokens: int = Field(description="最大输出 token", default=2000)


class SourceConfig(BaseModel):
    """数据源配置（供 Agent 参考）"""

    rss: list[dict[str, str]] = Field(
        description="RSS 源列表",
        default_factory=lambda: [
            {"url": "https://openai.com/blog/rss.xml", "name": "OpenAI Blog"},
            {"url": "https://huggingface.co/blog/feed.xml", "name": "Hugging Face Blog"},
        ]
    )
    hacker_news: dict[str, Any] = Field(
        description="HN 配置",
        default_factory=lambda: {"min_points": 150}
    )
    github_trending: dict[str, Any] = Field(
        description="GitHub Trending 配置",
        default_factory=lambda: {"languages": ["python", "typescript"], "since": "daily"}
    )


class OutputConfig(BaseModel):
    """输出配置"""

    directory: str = Field(description="One-Pager 输出目录", default="~/.harness/scraper")


class ScraperConfig(BaseModel):
    """完整配置"""

    llm: LLMConfig = Field(default_factory=LLMConfig)
    sources: SourceConfig = Field(default_factory=SourceConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
