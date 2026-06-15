"""
IntelAgent - General-purpose information extraction agent powered by Harness SDK.

Uses AgentHarness with custom tools for:
- RSS fetching
- Hacker News fetching
- GitHub Trending fetching
- URL content fetching
- HKEX (Hong Kong Stock Exchange) announcements
- Financial news (Cailian, Wallstreetcn)
- One-Pager saving

The agent can be specialized via skill files (e.g., AI intelligence, HK stocks).
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
    FetchHKEXTool,
    FetchFinancialNewsTool,
)

logger = logging.getLogger(__name__)

# Skill directory: repo-local skills only
# skills/ is at packages/scraper/skills/
REPO_SKILL_DIR = Path(__file__).parent.parent.parent / "skills"

# Base system prompt - generic methodology, no domain-specific knowledge
BASE_SYSTEM_PROMPT = """# 信息提取代理

## 角色定位

你是一个专业的信息提取代理，负责从海量内容中识别高价值信息。

## 通用工作流程

### 第一步：数据采集
根据【技能文件】指引，选择合适的数据源工具。

### 第二步：精准筛选
根据【技能文件】中定义的判断标准，识别高价值内容。

### 第三步：深度挖掘
对通过筛选的内容，使用 `fetch_url` 获取详细信息。

### 第四步：结构化输出
使用 `save_one_pager` 保存，格式和 domain 参数参考技能文件。

## 通用判断原则

1. **宁缺毋滥**：宁可漏掉也不要误报
2. **时效性**：关注首次出现时间
3. **可操作性**：读者能从情报中获得价值
4. **区分热度与创新**：高热度 ≠ 高价值

## 技能注入

当前会话已加载领域技能。
技能文件包含：
- 工具清单和使用场景
- 领域特定的判断标准
- 已知实体列表（如成熟项目）
- One-Pager 模板
- 输出要求

请严格按照技能文件中的标准执行任务。
"""


def load_skill(skill_name: str) -> str | None:
    """
    Load skill content from skills directories.

    Priority:
    1. Repo-local skills (./skills/ in the repository)

    Args:
        skill_name: Skill file name (without .md extension)

    Returns:
        Skill content or None if not found
    """
    # Try repo-local skills first (for CI/CD)
    repo_skill_path = REPO_SKILL_DIR / f"{skill_name}.md"
    if repo_skill_path.exists():
        logger.info(f"Loaded skill from repo: {repo_skill_path}")
        return repo_skill_path.read_text(encoding="utf-8")

    return None


class IntelAgent:
    """
    General-purpose information extraction agent powered by Harness SDK.

    Can be specialized via skill files for different domains:
    - AI intelligence extraction
    - Stock market analysis
    - Custom domains

    Example:
        ```python
        from harness_scraper.agent import IntelAgent
        from harness_scraper.config import load_config

        # With AI intelligence skill
        agent = IntelAgent(load_config(), skill="ai-intelligence")
        result = await agent.run("Extract AI intelligence from RSS and HN")

        # With stock analysis skill
        agent = IntelAgent(load_config(), skill="stock-analysis")
        result = await agent.run("Extract stock market signals")

        # Without skill (generic mode)
        agent = IntelAgent(load_config())
        result = await agent.run("Extract trending tech topics")
        ```
    """

    def __init__(
        self,
        config: ScraperConfig,
        tools: list[Tool] | None = None,
        skill: str | None = None,
        memory_path: str | Path | None = None,
    ):
        """
        Initialize Intel Agent.

        Args:
            config: Scraper configuration with LLM settings
            tools: Optional custom tools (defaults to all intel tools)
            skill: Optional skill name (e.g., "ai-intelligence", "hk-stocks-alpha")
                   Loads from packages/scraper/skills/{skill}.md
            memory_path: Optional memory file path for known entities
        """
        self.config = config
        self.skill = skill

        # Default tools - all intel and financial tools
        if tools is None:
            tools = [
                FetchRSSTool(),
                FetchHNTool(),
                FetchShowHNTool(),
                FetchGitHubTrendingTool(),
                FetchURLTool(),
                SaveOnePagerTool(),
                FetchHKEXTool(),
                FetchFinancialNewsTool(),
            ]

        # Build system prompt
        system_prompt = BASE_SYSTEM_PROMPT

        # Load and inject skill if specified
        if skill:
            skill_content = load_skill(skill)
            if skill_content:
                system_prompt += f"\n\n---\n\n# 已加载技能：{skill}\n\n{skill_content}"
                logger.info(f"Loaded skill: {skill}")
            else:
                logger.warning(f"Skill not found: {skill} (checked {REPO_SKILL_DIR})")

        # Convert memory_path to Path if string
        if memory_path:
            memory_path = Path(str(memory_path).replace("~", str(Path.home())))

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
        prompt: str = "运行信息提取：从 RSS、HN、GitHub Trending 获取内容，识别高价值信息，生成 One-Pager",
        session_id: str | None = None,
        verbose: bool = False,
    ) -> Any:
        """
        Run the information extraction agent.

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
        prompt_parts = ["运行信息提取："]

        if rss_feeds:
            for feed in rss_feeds[:5]:  # Limit to 5 feeds
                prompt_parts.append(f"使用 fetch_rss 抓取 {feed}")

        prompt_parts.append(f"使用 fetch_hn 抓取 HN 帖子（min_points={hn_min_points}）")
        prompt_parts.append(f"使用 fetch_show_hn 抓取 Show HN（min_points={show_hn_min_points}）")
        prompt_parts.append(f"使用 fetch_github_trending 抓取 {github_language} trending")

        prompt_parts.append("识别高价值信息，对有潜力的内容使用 fetch_url 深度抓取")
        prompt_parts.append("使用 save_one_pager 保存情报一页纸")

        prompt = "\n".join(prompt_parts)

        return await self.run(prompt=prompt, verbose=verbose)

    def get_session(self, session_id: str) -> Any:
        """Get an existing session."""
        return self._agent.get_session(session_id)

    def clear_session(self, session_id: str) -> None:
        """Clear a session's messages."""
        self._agent.clear_session(session_id)
