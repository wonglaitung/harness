"""
Windows event loop policy setup.

This MUST be imported before any asyncio/qasync imports on Windows.
It should be the very first import in the entry point.
"""

import sys

if sys.platform == "win32":
    import asyncio
    # Force SelectorEventLoop to fix qasync crashes on Windows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
