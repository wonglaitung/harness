"""
Mock LLM example - demonstrates agent behavior without real API calls.

This example uses MockLLMClient to simulate LLM responses,
useful for testing and development without API costs.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from harness import AgentHarness, ReadTool
from harness.llm.mock import MockLLMClient, create_tool_use_mock
from harness.sdk.config import HarnessConfig


async def main():
    """Run agent with mock LLM."""

    # Create mock LLM with predefined responses
    mock_llm = MockLLMClient()
    mock_llm.add_response(
        MockLLMClient.MockResponse(
            content="I will help you analyze the project. Let me read the main file.",
            tool_calls=[
                {"id": "call_1", "name": "read", "arguments": {"file_path": "pyproject.toml"}}
            ],
            stop_reason="tool_use",
        )
    )
    mock_llm.add_response(
        MockLLMClient.MockResponse(
            content="Based on the pyproject.toml, this is a Python SDK for AI agents called 'harness-sdk'. It provides an embeddable framework for building AI agents with tools, memory, and skills.",
            stop_reason="end_turn",
        )
    )

    print("=== Mock LLM Example ===")

    # Create agent (we'll inject the mock LLM manually)
    # Note: This requires modifying AgentHarness to accept custom LLM client
    # For now, we demonstrate the mock client directly

    # Simulate what the agent would do
    print("\n1. User asks: 'Analyze this project'")
    print("\n2. Mock LLM responds:")
    response1 = await mock_llm.call(
        messages=[{"role": "user", "content": "Analyze this project"}],
        tools=[{"name": "read", "description": "Read file", "input_schema": {"type": "object"}}],
    )
    print(f"   Content: {response1.content}")
    print(f"   Tool calls: {response1.tool_calls}")

    print("\n3. Tool executed: read(pyproject.toml)")
    print("   (Tool result would be returned)")

    print("\n4. Mock LLM responds with analysis:")
    response2 = await mock_llm.call(
        messages=[
            {"role": "user", "content": "Analyze this project"},
            {"role": "assistant", "content": response1.content},
            {"role": "tool", "content": "file contents..."},
        ],
    )
    print(f"   Content: {response2.content}")

    print(f"\nTotal mock calls: {mock_llm.call_count}")


if __name__ == "__main__":
    # Import MockResponse
    from harness.llm.mock import MockResponse
    asyncio.run(main())