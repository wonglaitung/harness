"""
Main entry point for Harness Client.
"""

import sys
from pathlib import Path

# Add SDK to path for development
sdk_path = Path(__file__).parent.parent.parent.parent / "sdk" / "src"
if sdk_path.exists():
    sys.path.insert(0, str(sdk_path))

from harness_client.app import run


def main():
    """Main entry point."""
    run()


if __name__ == "__main__":
    main()
