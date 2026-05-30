"""
Main entry point for Harness Client.
"""

# CRITICAL: This MUST be the first import to set Windows event loop policy
import harness_client._win_event_loop

from harness_client.app import run


def main():
    """Main entry point."""
    run()


if __name__ == "__main__":
    main()
