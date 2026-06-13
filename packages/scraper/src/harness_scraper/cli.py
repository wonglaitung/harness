#!/usr/bin/env python3
"""
Harness Scraper CLI.

Usage:
    harness-scraper run              # Run continuously
    harness-scraper run --once       # Run once
    harness-scraper config           # Create default config
    harness-scraper config --show    # Show current config
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime, timedelta

from harness_scraper.config import load_config, create_default_config_file
from harness_scraper.scheduler import ScraperScheduler


def setup_logging(verbose: bool = False):
    """Configure logging"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def cmd_run(args):
    """Run scraper"""
    setup_logging(args.verbose)
    config = load_config()
    scheduler = ScraperScheduler(config)

    if args.once:
        since = datetime.now() - timedelta(hours=args.hours)
        asyncio.run(scheduler.run_once(since=since))
    else:
        asyncio.run(scheduler.run(interval_hours=args.interval))


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
        description="AI Intelligence Extraction System",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # run command
    run_parser = subparsers.add_parser("run", help="Run scraper")
    run_parser.add_argument("--once", action="store_true", help="Run once and exit")
    run_parser.add_argument("--interval", type=int, default=12, help="Hours between runs (default: 12)")
    run_parser.add_argument("--hours", type=int, default=12, help="Hours to look back (default: 12)")
    run_parser.set_defaults(func=cmd_run)

    # config command
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_parser.add_argument("--show", action="store_true", help="Show current config")
    config_parser.set_defaults(func=cmd_config)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
