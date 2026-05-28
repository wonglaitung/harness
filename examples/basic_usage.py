"""
Basic usage example for Harness SDK.

This example demonstrates how to create and use an agent
with basic file tools.
"""

import asyncio
import os
from pathlib import Path

# Add src to path for development
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from harness import AgentHarness, ReadTool, WriteTool, GlobTool


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

    # Example 1: List Python files
    print("\n--- Example 1: List Python files ---")
    result = await agent.run("Use glob to find all Python files in the current directory")
    print(f"Response: {result.content[:500]}...")
    print(f"Iterations: {result.iterations}")

    # Example 2: Read and analyze a file
    print("\n--- Example 2: Read a file ---")
    result = await agent.run(
        "Read the pyproject.toml file and summarize what this project is about",
        session_id="demo-session",  # Use same session for context
    )
    print(f"Response: {result.content[:500]}...")

    # Example 3: Multi-turn conversation
    print("\n--- Example 3: Multi-turn conversation ---")
    result = await agent.run(
        "Based on what you read, what are the main dependencies?",
        session_id="demo-session",
    )
    print(f"Response: {result.content[:500]}...")

    print("\n--- Done ---")


if __name__ == "__main__":
    asyncio.run(main())