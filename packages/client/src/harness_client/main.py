"""
Main entry point for Harness Client.
"""

import sys

# CRITICAL: Must be set BEFORE importing asyncio/qasync on Windows
# This fixes qasync crashes caused by ProactorEventLoop incompatibility
if sys.platform == "win32":
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from harness_client.app import run


def main():
    """Main entry point."""
    run()


if __name__ == "__main__":
    main()
