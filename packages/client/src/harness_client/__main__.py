"""
Main entry point for running harness_client as a module.

Usage: python -m harness_client
"""

# CRITICAL: This MUST be the first import to set Windows event loop policy
import harness_client._win_event_loop

from harness_client.main import main

if __name__ == "__main__":
    main()
