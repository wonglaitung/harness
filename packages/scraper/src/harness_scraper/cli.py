#!/usr/bin/env python3
"""
Harness Scraper CLI.

Usage:
    harness-scraper agent            # Run SDK agent (default: extract from all sources)
    harness-scraper agent "prompt"   # Run agent with custom prompt
    harness-scraper config           # Create default config
    harness-scraper config --show    # Show current config
"""

import argparse
import asyncio
import logging
import sys

from harness_scraper.config import load_config, create_default_config_file


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

    from harness_scraper.agent import IntelAgent

    agent = IntelAgent(
        config=config,
        memory_path="~/.harness/scraper/MEMORY.md",
    )

    # Build prompt
    if args.prompt:
        prompt = args.prompt
    else:
        prompt = """运行情报抽取：

1. 使用 fetch_rss 抓取以下 RSS 源：
   - https://openai.com/blog/rss.xml
   - https://huggingface.co/blog/feed.xml

2. 使用 fetch_hn 抓取 Hacker News 高分帖子 (min_points=150)

3. 使用 fetch_show_hn 抓取 Show HN 早期新项目 (min_points=50)

4. 使用 fetch_github_trending 抓取 Python 和 TypeScript trending

对发现的新范式项目：
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


def main():
    parser = argparse.ArgumentParser(
        prog="harness-scraper",
        description="AI Intelligence Extraction System (SDK Agent)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # agent command (default)
    agent_parser = subparsers.add_parser("agent", help="Run SDK agent for intelligence extraction")
    agent_parser.add_argument("prompt", nargs="?", help="Custom prompt for the agent")
    agent_parser.set_defaults(func=cmd_agent)

    # config command
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_parser.add_argument("--show", action="store_true", help="Show current config")
    config_parser.set_defaults(func=cmd_config)

    args = parser.parse_args()

    # Default to agent command
    if not args.command:
        args.command = "agent"
        args.prompt = None
        args.func = cmd_agent

    args.func(args)


if __name__ == "__main__":
    main()
