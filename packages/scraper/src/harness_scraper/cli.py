#!/usr/bin/env python3
"""
Harness Scraper CLI.

Usage:
    harness-scraper                           # Run with ai-intelligence skill (default)
    harness-scraper --skill hk-stocks-alpha   # Run with HK stocks skill
    harness-scraper --skill custom            # Run with custom skill
    harness-scraper agent "prompt"            # Run agent with custom prompt
    harness-scraper config                    # Create default config
    harness-scraper config --show             # Show current config
    harness-scraper skills                    # List available skills
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from harness_scraper.config import load_config, create_default_config_file
from harness_scraper.agent import IntelAgent, REPO_SKILL_DIR

# Default output directory for One-Pagers
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent.parent / "output"


def setup_logging(verbose: bool = False):
    """Configure logging"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def cmd_agent(args):
    """Run SDK agent (autonomous intelligence extraction)"""
    setup_logging(args.verbose)
    config = load_config()

    # Ensure output directory exists
    output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Tools are now auto-selected from skill's tools.allowed frontmatter
    agent = IntelAgent(
        config=config,
        skill=args.skill,
        memory_path=output_dir / "MEMORY.md",
    )

    # Build prompt
    if args.prompt:
        prompt = args.prompt
    else:
        # Default prompts based on skill
        if args.skill == "hk-stocks-alpha":
            prompt = """运行港股 Alpha 捕获：

1. 使用 fetch_hkex 抓取港交所公告（回购、减持）
2. 使用 fetch_financial_news 获取财经快讯

识别左侧信号（回购潮、政策事件），生成交易快报"""
        elif args.skill:
            prompt = f"""运行情报抽取（技能：{args.skill}）：

根据技能文件定义的工作流程执行，使用技能指定的工具。

识别高价值信息，生成 One-Pager"""
        else:
            # Default: AI intelligence
            prompt = """运行 AI 情报抽取：

1. 使用 fetch_rss 抓取以下 RSS 源：
   - https://openai.com/blog/rss.xml
   - https://huggingface.co/blog/feed.xml

2. 使用 fetch_hn 抓取 Hacker News 高分帖子 (min_points=150)

3. 使用 fetch_show_hn 抓取 Show HN 早期新项目 (min_points=50)

4. 使用 fetch_github_trending 抓取 Python 和 TypeScript trending

识别新范式项目：
- 使用 fetch_url 深度抓取 README
- 使用 save_one_pager 保存情报一页纸"""

    result = asyncio.run(agent.run(prompt=prompt, verbose=args.verbose))
    print("\n=== Agent Result ===")
    print(result.content)


def cmd_config(args):
    """Manage config"""
    if args.show:
        config = load_config()
        print(f"LLM: {config.llm.provider} @ {config.llm.base_url}")
        print(f"Model: {config.llm.model}")
        print(f"Output: {config.output.directory}")
        print(f"RSS sources: {len(config.sources.rss)}")
    else:
        path = create_default_config_file()
        print(f"Created config file: {path}")
        print("Edit it to add your API key and customize sources.")


def cmd_skills(args):
    """List available skills"""
    skill_dir = REPO_SKILL_DIR
    if not skill_dir.exists():
        print(f"Skill directory not found: {skill_dir}")
        print(f"Create skill files in {skill_dir} directory.")
        return

    skill_files = list(skill_dir.glob("*.md"))
    if not skill_files:
        print(f"No skill files found in {skill_dir}")
        print("\nExample skills:")
        print("  - ai-intelligence.md  # AI intelligence extraction")
        print("  - hk-stocks-alpha.md   # HK stock analysis")
        return

    print(f"Available skills in {skill_dir}:\n")
    for skill_file in sorted(skill_files):
        skill_name = skill_file.stem
        print(f"  --skill {skill_name}")

    print("\nUsage:")
    print(f"  harness-scraper --skill {skill_files[0].stem}")


def main():
    parser = argparse.ArgumentParser(
        prog="harness-scraper",
        description="AI Intelligence Extraction System (SDK Agent)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--skill",
        type=str,
        default=None,
        help="Skill to load (e.g., ai-intelligence, hk-stocks-alpha). Default: ai-intelligence",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # agent command (default)
    agent_parser = subparsers.add_parser("agent", help="Run SDK agent for intelligence extraction")
    agent_parser.add_argument("prompt", nargs="?", help="Custom prompt for the agent")
    agent_parser.set_defaults(func=cmd_agent)

    # config command
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_parser.add_argument("--show", action="store_true", help="Show current config")
    config_parser.set_defaults(func=cmd_config)

    # skills command
    skills_parser = subparsers.add_parser("skills", help="List available skills")
    skills_parser.set_defaults(func=cmd_skills)

    args = parser.parse_args()

    # Default to agent command with ai-intelligence skill
    if not args.command:
        args.command = "agent"
        args.prompt = None
        # Set default skill if not specified
        if args.skill is None:
            args.skill = "ai-intelligence"
        args.func = cmd_agent

    args.func(args)


if __name__ == "__main__":
    main()
