"""
GoalAgent - Goal-driven information extraction agent.

Uses AgentHarness.run_goal() for autonomous execution until goals are achieved.
This follows the Loop Engineering paradigm from Harness SDK.
"""

import logging
from pathlib import Path
from typing import Any, Callable

from harness import AgentHarness, GoalStatus
from harness.loop import GoalConfig, GoalResult
from harness.skills.base import Skill
from harness.tools.base import Tool

from harness_scraper.models import ScraperConfig
from harness_scraper.tools import get_tools_by_names

logger = logging.getLogger(__name__)

# Skill directory: repo-local skills only
REPO_SKILL_DIR = Path(__file__).parent.parent.parent / "skills"

# Base system prompt - minimal, skill drives everything
BASE_SYSTEM_PROMPT = """# 信息提取代理

## 角色定位

你是一个专业的信息提取代理，负责从海量内容中识别高价值信息。

## 通用判断原则

1. **宁缺毋滥**：宁可漏掉也不要误报
2. **时效性**：关注首次出现时间
3. **可操作性**：读者能从情报中获得价值
4. **区分热度与创新**：高热度 ≠ 高价值
"""


def load_skill(skill_name: str) -> Skill | None:
    """Load skill from skills directory."""
    repo_skill_path = REPO_SKILL_DIR / f"{skill_name}.md"
    if repo_skill_path.exists():
        logger.info(f"Loaded skill from repo: {repo_skill_path}")
        return Skill.from_file(repo_skill_path)
    return None


class GoalAgent:
    """
    Goal-driven information extraction agent.

    Uses run_goal() to autonomously execute until verification criteria are met.
    This is more intelligent than one-shot execution - the agent will:
    - Fetch multiple sources
    - Analyze content quality
    - Refine searches based on initial findings
    - Continue until goal is achieved

    Example:
        ```python
        from harness_scraper.goal_agent import GoalAgent
        from harness_scraper.config import load_config

        # Simple goal
        agent = GoalAgent(load_config(), skill="ai-intelligence")
        result = await agent.run_goal(
            "提取 3 个 AI 行业新范式项目",
            max_iterations=20,
        )

        # Custom verification
        def verify(result):
            # Check if 3 one-pagers were saved
            output_dir = Path("output")
            return len(list(output_dir.glob("*.md"))) >= 3

        result = await agent.run_goal(
            "提取 AI 情报",
            custom_verifier=verify,
        )

        if result.status == GoalStatus.ACHIEVED:
            print(f"Goal achieved in {result.total_iterations} iterations")
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
        Initialize Goal Agent.

        Args:
            config: Scraper configuration with LLM settings
            tools: Optional custom tools (if None, auto-selected from skill)
            skill: Optional skill name (e.g., "ai-intelligence", "hk-stocks-alpha")
            memory_path: Optional memory file path for known entities
        """
        self.config = config
        self.skill_name = skill
        self._skill: Skill | None = None

        # Load skill if specified
        if skill:
            self._skill = load_skill(skill)
            if not self._skill:
                raise ValueError(f"Skill not found: {skill} (checked {REPO_SKILL_DIR})")
            logger.info(f"Loaded skill: {self._skill.name}")

        # Tools selection
        if tools is None:
            if self._skill and self._skill.tools.allowed:
                tools = get_tools_by_names(self._skill.tools.allowed)
                logger.info(f"Auto-selected tools: {[t.name for t in tools]}")
            else:
                tools = get_tools_by_names(["fetch_url"])
                logger.info("Using minimal default tools: [fetch_url]")

        # Build system prompt
        system_prompt = BASE_SYSTEM_PROMPT
        if self._skill:
            system_prompt += f"\n\n---\n\n# 已加载技能：{self._skill.name}\n\n{self._skill.content}"

        # Convert memory_path
        if memory_path:
            memory_path = Path(str(memory_path).replace("~", str(Path.home())))

        # Create AgentHarness
        self._agent = AgentHarness(
            model=config.llm.model,
            api_key=config.llm.api_key,
            base_url=config.llm.base_url,
            provider="openai",
            tools=tools,
            system_prompt=system_prompt,
            memory_md_path=memory_path,
            max_iterations=25,  # Higher limit for goal-driven execution
        )

    async def run_goal(
        self,
        goal: str,
        success_criteria: str | None = None,
        max_iterations: int = 20,
        max_context_resets: int = 3,
        timeout_seconds: int = 1800,
        custom_verifier: Callable[[GoalResult], bool] | None = None,
        on_progress: Callable[[Any], None] | None = None,
    ) -> GoalResult:
        """
        Run goal-driven information extraction.

        The agent will autonomously execute until:
        - Goal is verified as achieved
        - Max iterations reached
        - Timeout exceeded
        - Context window exhausted

        Args:
            goal: Goal description (e.g., "提取 3 个 AI 新范式项目")
            success_criteria: Optional explicit success criteria
            max_iterations: Maximum iterations per context window
            max_context_resets: Maximum context reset attempts
            timeout_seconds: Total execution timeout (default 30 min)
            custom_verifier: Optional custom verification function
            on_progress: Optional progress callback

        Returns:
            GoalResult with status, iterations, and verification log
        """
        logger.info(f"Running GoalAgent with goal: {goal[:50]}...")

        result = await self._agent.run_goal(
            goal=goal,
            success_criteria=success_criteria,
            workspace_dir=str(Path.cwd()),
            max_iterations=max_iterations,
            max_context_resets=max_context_resets,
            timeout_seconds=timeout_seconds,
            custom_verifier=custom_verifier,
            on_progress=on_progress,
        )

        if result.status == GoalStatus.ACHIEVED:
            logger.info(f"Goal achieved in {result.total_iterations} iterations")
        else:
            logger.warning(f"Goal not achieved: {result.status} after {result.total_iterations} iterations")

        return result

    async def run(
        self,
        prompt: str,
        session_id: str | None = None,
        verbose: bool = False,
    ) -> Any:
        """
        Run one-shot execution (fallback for simple cases).

        For complex extraction tasks, prefer run_goal() instead.
        """
        logger.info(f"Running one-shot IntelAgent with prompt: {prompt[:50]}...")
        return await self._agent.run(
            prompt=prompt,
            session_id=session_id,
            verbose=verbose,
        )

    def get_session(self, session_id: str) -> Any:
        """Get an existing session."""
        return self._agent.get_session(session_id)

    def clear_session(self, session_id: str) -> None:
        """Clear a session's messages."""
        self._agent.clear_session(session_id)