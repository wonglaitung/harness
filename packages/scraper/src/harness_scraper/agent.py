"""
IntelAgent - Intelligence extraction agent powered by Harness SDK.

Uses AgentHarness with custom tools for:
- RSS fetching
- Hacker News fetching
- GitHub Trending fetching
- URL content fetching
- One-Pager saving

The agent can autonomously decide which sources to fetch,
judge if content represents new paradigms, and generate One-Pagers.
"""

import logging
from pathlib import Path
from typing import Any

from harness import AgentHarness
from harness.tools.base import Tool

from harness_scraper.models import ScraperConfig
from harness_scraper.tools import (
    FetchRSSTool,
    FetchHNTool,
    FetchShowHNTool,
    FetchGitHubTrendingTool,
    FetchURLTool,
    SaveOnePagerTool,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个 AI 情报提取代理，负责从网络源中识别新范式、新工具和新概念。

你拥有以下工具：
- fetch_rss: 抓取 RSS 文章
- fetch_hn: 抓取 Hacker News 高分帖子 (>=150 points)
- fetch_show_hn: 抓取 Show HN 帖子 (>=50 points，适合发现早期新项目)
- fetch_github_trending: 抓取 GitHub Trending AI 项目
- fetch_url: 深度抓取 URL 内容（GitHub README 或网页内容）
- save_one_pager: 保存情报一页纸

你的任务是：
1. 从各个数据源获取内容
2. 判断哪些内容代表新的技术范式（如 taste-skill、vibe-coding、MCP）
3. 对于有潜力的内容，使用 fetch_url 深度抓取
4. 使用 save_one_pager 保存情报

判断标准：
- TRUE: 新项目（<3个月）、新范式/黑话、新标准/协议
- FALSE: 成熟项目（vLLM、LangChain）、教程、增量更新、纯应用实现

已知成熟项目（应跳过）：
- vLLM、LangChain、LlamaIndex、Ollama、Transformers

请自主决定抓取顺序和判断逻辑，生成的 One-Pager 必须使用中文。"""


class IntelAgent:
    """
    Intelligence extraction agent powered by Harness SDK.

    Example:
        ```python
        from harness_scraper.agent import IntelAgent
        from harness_scraper.config import load_config

        agent = IntelAgent(load_config())
        result = await agent.run("Extract AI intelligence from RSS and HN")
        print(result.content)
        ```
    """

    def __init__(
        self,
        config: ScraperConfig,
        tools: list[Tool] | None = None,
        memory_path: str | Path | None = None,
    ):
        """
        Initialize Intel Agent.

        Args:
            config: Scraper configuration with LLM settings
            tools: Optional custom tools (defaults to all intel tools)
            memory_path: Optional memory file path for known projects
        """
        self.config = config

        # Default tools
        if tools is None:
            tools = [
                FetchRSSTool(),
                FetchHNTool(),
                FetchShowHNTool(),
                FetchGitHubTrendingTool(),
                FetchURLTool(),
                SaveOnePagerTool(),
            ]

        # Build system prompt
        system_prompt = SYSTEM_PROMPT

        # Convert memory_path to Path if string
        if memory_path:
            memory_path = Path(str(memory_path).replace("~", str(Path.home())))
            if memory_path.exists():
                system_prompt += f"\n\n## 记忆文件\n请参考 {memory_path} 中记录的已知项目。"

        # Create AgentHarness
        self._agent = AgentHarness(
            model=config.llm.model,
            api_key=config.llm.api_key,
            base_url=config.llm.base_url,
            provider="openai",  # All compatible APIs use OpenAI provider
            tools=tools,
            system_prompt=system_prompt,
            memory_md_path=memory_path,
            max_iterations=15,  # Allow enough iterations for full workflow
        )

    async def run(
        self,
        prompt: str = "运行情报抽取：从 RSS、HN、GitHub Trending 获取内容，识别新范式，生成 One-Pager",
        session_id: str | None = None,
        verbose: bool = False,
    ) -> Any:
        """
        Run the intelligence extraction agent.

        Args:
            prompt: User prompt describing what to extract
            session_id: Optional session ID for conversation continuity
            verbose: If True, print progress to console

        Returns:
            LoopResult from AgentHarness
        """
        logger.info(f"Running IntelAgent with prompt: {prompt[:50]}...")

        result = await self._agent.run(
            prompt=prompt,
            session_id=session_id,
            verbose=verbose,
        )

        logger.info(f"IntelAgent completed: {len(result.content)} chars output")
        return result

    async def run_with_sources(
        self,
        rss_feeds: list[str] | None = None,
        hn_min_points: int = 150,
        show_hn_min_points: int = 50,
        github_language: str = "python",
        verbose: bool = False,
    ) -> Any:
        """
        Run agent with specific source parameters.

        Args:
            rss_feeds: List of RSS feed URLs to fetch
            hn_min_points: Minimum points for HN posts
            show_hn_min_points: Minimum points for Show HN posts
            github_language: Language filter for GitHub Trending
            verbose: If True, print progress

        Returns:
            LoopResult from AgentHarness
        """
        # Build specific prompt
        prompt_parts = ["运行情报抽取："]

        if rss_feeds:
            for feed in rss_feeds[:5]:  # Limit to 5 feeds
                prompt_parts.append(f"使用 fetch_rss 抓取 {feed}")

        prompt_parts.append(f"使用 fetch_hn 抓取 HN 帖子（min_points={hn_min_points}）")
        prompt_parts.append(f"使用 fetch_show_hn 抓取 Show HN（min_points={show_hn_min_points}）")
        prompt_parts.append(f"使用 fetch_github_trending 抓取 {github_language} trending")

        prompt_parts.append("识别新范式，对有潜力的内容使用 fetch_url 深度抓取")
        prompt_parts.append("使用 save_one_pager 保存情报一页纸")

        prompt = "\n".join(prompt_parts)

        return await self.run(prompt=prompt, verbose=verbose)

    def get_session(self, session_id: str) -> Any:
        """Get an existing session."""
        return self._agent.get_session(session_id)

    def clear_session(self, session_id: str) -> None:
        """Clear a session's messages."""
        self._agent.clear_session(session_id)