"""
Main entry point for Harness Client.
"""

import os
import sys
from pathlib import Path

# CRITICAL: This MUST be the first import to set Windows event loop policy

# Set tiktoken cache directory for bundled encoding files
# This is needed when running as a PyInstaller bundle
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    # sys._MEIPASS is the path to the bundled resources
    tiktoken_cache = Path(sys._MEIPASS) / "resources" / "tiktoken_cache"
    if tiktoken_cache.exists():
        os.environ["TIKTOKEN_CACHE_DIR"] = str(tiktoken_cache)

from harness_client.app import run


def main():
    """Main entry point."""
    run()


if __name__ == "__main__":
    main()
