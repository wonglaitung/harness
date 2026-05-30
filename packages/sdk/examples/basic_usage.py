"""
Basic usage example for Harness SDK.

This example demonstrates how to create and use an agent
with basic file tools, including progress tracking.
"""

import asyncio
import os
from pathlib import Path

# Add src to path for development
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from harness import (
    AgentHarness,
    ReadTool,
    WriteTool,
    GlobTool,
    ProgressEvent,
    ProgressEventType,
    create_progress_handler,
)


async def main():
    """Run basic agent example."""

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        print("Set it with: export ANTHROPIC_API_KEY=your-key-here")
        return

    # Create agent with file tools
    print("Creating agent with file tools...")
    agent = AgentHarness(
        model="claude-sonnet-4-6",
        tools=[ReadTool(), WriteTool(), GlobTool()],
    )

    # Example 1: Using verbose mode (simplest way to see progress)
    print("\n" + "=" * 60)
    print("Example 1: Using verbose=True for progress output")
    print("=" * 60)
    result = await agent.run(
        "Use glob to find all Python files in the current directory",
        verbose=True,  # This enables progress output
    )
    print(f"\nFinal response: {result.content[:300]}...")
    print(f"Iterations: {result.iterations}")

    # Example 2: Custom progress handler
    print("\n" + "=" * 60)
    print("Example 2: Custom progress handler")
    print("=" * 60)

    def my_progress_handler(event: ProgressEvent):
        """Custom handler that only shows tool calls and LLM calls."""
        if event.type == ProgressEventType.TOOL_CALL:
            print(f"  🔧 Tool: {event.data.get('tool', 'unknown')}")
        elif event.type == ProgressEventType.TOOL_RESULT:
            status = "✓" if event.data.get("success") else "✗"
            duration = f" ({event.duration_ms:.0f}ms)" if event.duration_ms else ""
            print(f"  {status} Completed{duration}")
        elif event.type == ProgressEventType.LLM_CALL:
            print(f"  🤖 Calling {event.data.get('model', 'LLM')}...")
        elif event.type == ProgressEventType.LOOP_END:
            print(f"  ✅ Done in {event.duration_ms:.0f}ms" if event.duration_ms else "  ✅ Done")

    result = await agent.run(
        "Read the pyproject.toml file and summarize what this project is about",
        session_id="demo-session",
        on_progress=my_progress_handler,
    )
    print(f"\nResponse: {result.content[:300]}...")

    # Example 3: Using create_progress_handler with different formats
    print("\n" + "=" * 60)
    print("Example 3: Using create_progress_handler")
    print("=" * 60)

    # Use colored output format
    colored_handler = create_progress_handler(format_style="colored")
    result = await agent.run(
        "What are the main dependencies?",
        session_id="demo-session",
        on_progress=colored_handler,
    )
    print(f"\nResponse: {result.content[:300]}...")

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())