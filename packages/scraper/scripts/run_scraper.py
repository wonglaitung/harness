#!/usr/bin/env python3
"""
Run Harness Scraper with timeout and collect generated reports.

Usage:
    python scripts/run_scraper.py --skill ai-intelligence --timeout 180
    python scripts/run_scraper.py --skill hk-stocks-alpha
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

from harness_scraper.config import load_config
from harness_scraper.agent import IntelAgent

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


def get_default_prompt(skill: str) -> str:
    """Get default prompt for a skill"""
    if skill == "ai-intelligence":
        return """运行 AI 情报抽取：

1. 使用 fetch_rss 抓取以下 RSS 源：
   - https://openai.com/blog/rss.xml
   - https://huggingface.co/blog/feed.xml

2. 使用 fetch_hn 抓取 Hacker News 高分帖子 (min_points=150)

3. 使用 fetch_show_hn 抓取 Show HN 早期新项目 (min_points=50)

4. 使用 fetch_github_trending 抓取 Python 和 TypeScript trending

识别新范式项目：
- 使用 fetch_url 深度抓取 README
- 使用 save_one_pager 保存情报一页纸（domain="ai"）"""

    elif skill == "hk-stocks-alpha":
        return """运行港股 Alpha 事件捕获：

1. 使用 fetch_hkex 获取港股异动数据
   - volume_threshold: 50000000 (50M HKD)
   - pct_threshold: 3.0

2. 使用 fetch_financial_news 获取财联社快讯
   - source: cailian
   - keywords: ['港股', '回购', '监管']
   - limit: 10

3. 使用 fetch_financial_news 获取宏观数据
   - source: macro

4. 分析异动事件，使用 save_one_pager 保存（domain="stocks"）

关注左侧信号：回购潮、版号获批、美联储降息预期、政策松绑
关注右侧信号：投行评级上调、港股通大额流入"""

    else:
        return f"""运行情报抽取（技能：{skill}）：

使用可用工具抓取相关内容，识别高价值信息，生成 One-Pager。"""


async def run_scraper(skill: str, timeout: int, verbose: bool = False) -> bool:
    """Run the scraper with timeout"""
    setup_logging(verbose)

    # Ensure output directory exists
    output_dir = DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load config
    config = load_config()

    # Create agent with skill
    agent = IntelAgent(
        config=config,
        skill=skill,
        memory_path=output_dir / "MEMORY.md",
    )

    # Get prompt
    prompt = get_default_prompt(skill)

    print(f"=== Running {skill} scraper (timeout: {timeout}s) ===")
    start_time = datetime.now()

    try:
        # Run with timeout
        result = await asyncio.wait_for(
            agent.run(prompt=prompt, verbose=verbose),
            timeout=timeout
        )

        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"=== Completed in {elapsed:.1f}s ===")

        # Show generated files
        today = datetime.now().strftime("%Y-%m-%d")
        domain = "ai" if skill == "ai-intelligence" else "stocks"
        files_dir = output_dir / today / domain

        if files_dir.exists():
            files = list(files_dir.glob("*.md"))
            print(f"Generated {len(files)} One-Pagers:")
            for f in files:
                print(f"  - {f.name}")
        else:
            print("No files generated")

        return True

    except asyncio.TimeoutError:
        print(f"=== Timeout after {timeout}s ===")
        return False
    except Exception as e:
        print(f"=== Error: {e} ===")
        return False


def main():
    parser = argparse.ArgumentParser(
        prog="run_scraper",
        description="Run Harness Scraper with timeout",
    )
    parser.add_argument(
        "--skill",
        type=str,
        default="ai-intelligence",
        help="Skill to run (ai-intelligence, hk-stocks-alpha)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="Timeout in seconds (default: 180)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    # Run scraper
    success = asyncio.run(run_scraper(
        skill=args.skill,
        timeout=args.timeout,
        verbose=args.verbose,
    ))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
