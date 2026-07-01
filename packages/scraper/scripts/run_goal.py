#!/usr/bin/env python3
"""
Run Harness Scraper with Goal-Driven execution.

Uses GoalAgent to autonomously execute until goals are achieved.
This is more intelligent than one-shot execution - the agent will:
- Fetch multiple sources
- Analyze content quality
- Refine searches based on initial findings
- Continue until goal is achieved

Usage:
    python scripts/run_goal.py --skill ai-intelligence --goal "提取3个AI新范式项目"
    python scripts/run_goal.py --skill hk-stocks-alpha --max-iterations 30
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add packages to path
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "sdk" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "scraper" / "src"))

from harness import GoalStatus
from harness_scraper.config import load_config
from harness_scraper.goal_agent import GoalAgent
from harness_scraper.tools import (
    # AI intelligence tools
    FetchRSSTool, FetchHNTool, FetchShowHNTool,
    FetchGitHubTrendingTool, FetchURLTool, SaveOnePagerTool,
    # Stock/financial tools
    FetchHKEXTool, FetchFinancialNewsTool,
)

# Default output directory for One-Pagers
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent / "output"


def setup_logging(verbose: bool = False):
    """Configure logging"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def get_default_goal(skill: str) -> str:
    """Get default goal for a skill"""
    if skill == "ai-intelligence":
        return """提取 AI 行业情报，找到 3 个以上的新范式项目：

1. 抓取 OpenAI 和 HuggingFace RSS 博客
2. 抓取 Hacker News 高分帖子（>150 points）
3. 抓取 Show HN 新项目（>50 points）
4. 抓取 GitHub Python/TypeScript trending

对每个潜在新范式项目：
- 深度抓取 README 分析概念创新性
- 验证：新概念 + 首发<6月 + 社区共鸣
- 保存 One-Pager 到 output/YYYY-MM-DD/ai/

目标达成标准：生成至少 3 个高质量 One-Pager"""

    elif skill == "hk-stocks-alpha":
        return """提取港股 Alpha 信号，识别 3 个以上左侧交易机会：

1. 获取港交所异动数据（成交额>50M, 涨跌幅>3%）
2. 获取财联社港股快讯（回购、监管、政策）
3. 获取宏观经济数据

分析信号类型：
- 左侧信号：回购潮、政策松绑、美联储降息预期
- 右侧信号：投行评级上调、港股通大额流入

保存分析报告到 output/YYYY-MM-DD/stocks/

目标达成标准：生成至少 3 个 Alpha 信号分析"""

    else:
        return f"""根据技能 {skill} 提取高价值信息，生成至少 2 个 One-Pager。"""


def get_verification_criteria(skill: str) -> str:
    """Get explicit success criteria for goal verification"""
    if skill == "ai-intelligence":
        return "生成至少 3 个 One-Pager，每个包含：项目名、新概念定义、首发时间、社区热度证据"
    elif skill == "hk-stocks-alpha":
        return "生成至少 3 个 Alpha 信号分析，每个包含：信号类型、相关股票、触发原因、风险评估"
    else:
        return "生成至少 2 个高质量情报报告"


async def run_goal(
    skill: str,
    goal: str | None,
    max_iterations: int,
    timeout_seconds: int,
    verbose: bool = False,
) -> bool:
    """Run goal-driven scraper"""
    setup_logging(verbose)

    # Ensure output directory exists
    output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load config
    config = load_config()

    # Create GoalAgent
    agent = GoalAgent(
        config=config,
        skill=skill,
        memory_path=output_dir / "MEMORY.md",
    )

    # Get goal and criteria
    if goal is None:
        goal = get_default_goal(skill)
    success_criteria = get_verification_criteria(skill)

    print(f"\n🎯 Goal: {goal[:100]}...")
    print(f"📋 Success Criteria: {success_criteria}")
    print(f"⏱️ Max Iterations: {max_iterations}, Timeout: {timeout_seconds}s\n")

    start_time = datetime.now()

    try:
        result = await agent.run_goal(
            goal=goal,
            success_criteria=success_criteria,
            max_iterations=max_iterations,
            timeout_seconds=timeout_seconds,
        )

        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n=== Result ===")
        print(f"Status: {result.status}")
        print(f"Iterations: {result.total_iterations}")
        print(f"Elapsed: {elapsed:.1f}s")

        if result.status == GoalStatus.ACHIEVED:
            print("✅ Goal achieved!")
        elif result.status == GoalStatus.MAX_ITERATIONS:
            print("⚠️ Max iterations reached (partial progress)")
        elif result.status == GoalStatus.TIMEOUT:
            print("⚠️ Timeout reached (partial progress)")
        else:
            print(f"❌ Goal not achieved: {result.status}")

        # Show generated files
        today = datetime.now().strftime("%Y-%m-%d")
        domain = "ai" if skill == "ai-intelligence" else "stocks"
        files_dir = output_dir / today / domain

        if files_dir.exists():
            files = list(files_dir.glob("*.md"))
            print(f"\nGenerated {len(files)} One-Pagers:")
            for f in files:
                print(f"  - {f.name}")
        else:
            print("\nNo files generated")

        return result.status == GoalStatus.ACHIEVED

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        prog="run_goal",
        description="Run Goal-Driven Scraper (autonomous until goal achieved)",
    )
    parser.add_argument(
        "--skill",
        type=str,
        default="ai-intelligence",
        help="Skill to run (ai-intelligence, hk-stocks-alpha)",
    )
    parser.add_argument(
        "--goal",
        type=str,
        default=None,
        help="Custom goal description (uses default if not specified)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=25,
        help="Max iterations (default: 25)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=1800,
        help="Timeout in seconds (default: 1800 = 30 min)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    # Run goal-driven scraper
    success = asyncio.run(run_goal(
        skill=args.skill,
        goal=args.goal,
        max_iterations=args.max_iterations,
        timeout_seconds=args.timeout,
        verbose=args.verbose,
    ))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()