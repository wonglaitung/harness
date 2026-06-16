"""
Example: Using Custom OpenAI-Compatible API with Harness SDK

This example demonstrates how to use Harness SDK with any
OpenAI-compatible API endpoint (e.g., xfyun, Azure, local LLM).

Key features:
- Custom API endpoint configuration
- Streaming output support
- Session management
- Error handling
"""

import asyncio
import os
from harness import AgentHarness
from harness.sdk.config import HarnessConfig


# =============================================================================
# Configuration
# =============================================================================


def get_custom_api_config():
    """
    Get configuration for custom OpenAI-compatible API.

    Supports:
    - xfyun (讯飞星火)
    - Azure OpenAI
    - Local LLM (e.g., llama.cpp, vLLM)
    - Any OpenAI-compatible proxy

    Environment variables (optional overrides):
    - HARNESS_API_KEY: Override API key
    - HARNESS_BASE_URL: Override base URL
    - HARNESS_MODEL: Override model name
    """
    return HarnessConfig.from_custom_api(
        api_key=os.getenv(
            "HARNESS_API_KEY",
            "16a9dd623e0d9970b082f7d5ba01475d:YmM2NzI5M2VjOGJjNzNmYjc1N2QzNTA1"
        ),
        base_url=os.getenv(
            "HARNESS_BASE_URL",
            "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2"
        ),
        model=os.getenv("HARNESS_MODEL", "xopglm5"),
        provider="openai",
        max_iterations=10,
    )


# =============================================================================
# Examples
# =============================================================================


async def example_basic_chat():
    """Example 1: Basic chat interaction."""
    print("\n" + "=" * 60)
    print("Example 1: Basic Chat")
    print("=" * 60)

    config = get_custom_api_config()
    agent = AgentHarness(config=config)

    result = await agent.run(prompt="What is the capital of France?")

    print(f"Response: {result.content}")
    print(f"Tokens used: {result.token_usage.total_tokens}")


async def example_streaming():
    """Example 2: Streaming output."""
    print("\n" + "=" * 60)
    print("Example 2: Streaming Output")
    print("=" * 60)

    config = get_custom_api_config()
    agent = AgentHarness(config=config)

    print("Response: ", end="", flush=True)

    async for chunk in agent.run_stream(prompt="Tell me a short story about a robot."):
        if chunk.type == "text":
            print(chunk.content, end="", flush=True)
        elif chunk.type == "tool_call":
            print(f"\n[Tool: {chunk.data.get('tool')}]", flush=True)
        elif chunk.type == "done":
            print("\n[Done]", flush=True)


async def example_session():
    """Example 3: Multi-turn conversation with session."""
    print("\n" + "=" * 60)
    print("Example 3: Multi-turn Conversation")
    print("=" * 60)

    config = get_custom_api_config()
    agent = AgentHarness(config=config)

    # First message
    result1 = await agent.run(
        prompt="My name is Alice. Remember that.",
        session_id="demo-session"
    )
    print(f"Turn 1: {result1.content[:100]}...")

    # Continue conversation
    result2 = await agent.run(
        prompt="What's my name?",
        session_id="demo-session"
    )
    print(f"Turn 2: {result2.content}")

    # Clear session
    agent.clear_session("demo-session")
    print("Session cleared.")


async def example_with_progress():
    """Example 4: Progress event handling."""
    print("\n" + "=" * 60)
    print("Example 4: Progress Events")
    print("=" * 60)

    config = get_custom_api_config()
    agent = AgentHarness(config=config)

    events = []

    def on_progress(event):
        events.append(event)
        print(f"  [{event.type.value}] {event.message or ''}")

    result = await agent.run(
        prompt="Calculate 25 * 4 + 10",
        on_progress=on_progress
    )

    print(f"\nTotal events: {len(events)}")
    print(f"Result: {result.content}")


async def example_tools():
    """Example 5: Using custom tools."""
    print("\n" + "=" * 60)
    print("Example 5: Custom Tools")
    print("=" * 60)

    from harness.tools import Tool, ToolResult

    # Define a simple tool
    class CalculatorTool(Tool):
        @property
        def name(self) -> str:
            return "calculator"

        @property
        def description(self) -> str:
            return "Simple calculator for basic math operations"

        @property
        def input_schema(self) -> dict:
            return {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Math expression to evaluate, e.g. '2+2'"
                    }
                },
                "required": ["expression"]
            }

        async def execute(self, args, ctx) -> ToolResult:
            try:
                # Simple eval (for demo only - not safe for production)
                result = eval(args["expression"])
                return ToolResult(success=True, output=str(result))
            except Exception as e:
                return ToolResult(success=False, error=str(e))

    config = get_custom_api_config()
    agent = AgentHarness(config=config)

    # Register tool
    agent.register_tool(CalculatorTool())

    result = await agent.run(
        prompt="Use the calculator to compute 15 * 3 + 7"
    )

    print(f"Response: {result.content}")


# =============================================================================
# Main
# =============================================================================


async def main():
    """Run all examples."""
    print("\n" + "#" * 60)
    print("# Harness SDK - Custom API Examples")
    print("#" * 60)

    await example_basic_chat()
    await example_streaming()
    await example_session()
    await example_with_progress()
    await example_tools()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())