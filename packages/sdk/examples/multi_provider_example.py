"""
Multi-provider LLM example - demonstrates using different LLM providers.

This example shows how to use Anthropic, OpenAI, and custom LLM clients.
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from harness import (
    AgentHarness,
    AnthropicClient,
    GlobTool,
    LLMClient,
    LLMConfig,
    OpenAIClient,
    ReadTool,
)


async def example_anthropic():
    """Example using Anthropic Claude."""
    print("=== Anthropic Claude Example ===")

    # Method 1: Using provider parameter
    agent = AgentHarness(
        model="claude-sonnet-4-6",
        provider="anthropic",  # Optional, auto-detected from model name
        tools=[ReadTool()],
    )

    # Method 2: Using explicit client
    anthropic_client = AnthropicClient(
        model="claude-sonnet-4-6",
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
    )
    agent = AgentHarness(  # noqa: F841
        llm_client=anthropic_client,
        tools=[ReadTool()],
    )

    print("Anthropic client configured.")


async def example_openai():
    """Example using OpenAI."""
    print("\n=== OpenAI Example ===")

    # Method 1: Using provider parameter
    agent = AgentHarness(
        model="gpt-4o",
        provider="openai",  # Optional, auto-detected from model name
        tools=[ReadTool()],
    )

    # Method 2: Using explicit client
    openai_client = OpenAIClient(
        model="gpt-4o",
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
    agent = AgentHarness(  # noqa: F841
        llm_client=openai_client,
        tools=[ReadTool()],
    )

    print("OpenAI client configured.")


async def example_openai_custom_endpoint():
    """Example using OpenAI-compatible endpoint (e.g., local LLM, Azure)."""
    print("\n=== Custom OpenAI Endpoint Example ===")

    # Ollama local LLM
    agent = AgentHarness(
        model="llama3",
        provider="openai",
        base_url="http://localhost:11434/v1",
        api_key="ollama",  # Ollama doesn't need a real key
        tools=[ReadTool()],
    )

    # Azure OpenAI
    agent = AgentHarness(  # noqa: F841
        model="gpt-4o",
        provider="openai",
        base_url="https://your-resource.openai.azure.com/openai/deployments/your-deployment",
        api_key=os.environ.get("AZURE_OPENAI_KEY"),
        tools=[ReadTool()],
    )

    print("Custom endpoint configured.")


async def example_custom_llm():
    """Example using a completely custom LLM client."""
    print("\n=== Custom LLM Client Example ===")

    from harness.types import LLMResponse, StopReason, TokenUsage

    class MyCustomLLM(LLMClient):
        """A simple custom LLM that echoes input."""

        @property
        def model_name(self) -> str:
            return "custom-echo"

        async def call(
            self,
            messages,
            tools=None,
            system=None,
            **kwargs,
        ) -> LLMResponse:
            # Simple echo implementation
            last_message = messages[-1] if messages else {}
            content = f"Echo: {last_message.get('content', '')}"

            return LLMResponse(
                content=content,
                tool_calls=[],
                stop_reason=StopReason.END_TURN,
                usage=TokenUsage(input_tokens=0, output_tokens=0),
            )

        async def stream(self, messages, tools=None, system=None, on_chunk=None, **kwargs):
            last_message = messages[-1] if messages else {}
            content = f"Echo: {last_message.get('content', '')}"
            if on_chunk:
                on_chunk(content)
            yield content

    # Use custom LLM
    custom_client = MyCustomLLM(LLMConfig(model="custom-echo"))
    agent = AgentHarness(
        llm_client=custom_client,
        tools=[ReadTool()],
    )

    # Run with custom LLM
    result = await agent.run("Hello, world!")
    print(f"Result: {result.final_response}")


async def example_config_file():
    """Example using configuration file."""
    print("\n=== Config File Example ===")

    # YAML config example (create config.yaml):
    """
    model: gpt-4o
    provider: openai
    max_tokens: 4096
    temperature: 0.7
    system_prompt: "You are a helpful assistant."
    """

    # Load from file
    # agent = AgentHarness.from_config("config.yaml")

    # Or use HarnessConfig directly
    from harness import HarnessConfig

    config = HarnessConfig(
        model="gpt-4o",
        provider="openai",
        max_tokens=4096,
        temperature=0.7,
        system_prompt="You are a helpful code assistant.",
    )

    agent = AgentHarness(config=config, tools=[ReadTool(), GlobTool()])  # noqa: F841
    print("Config-based agent configured.")


async def main():
    """Run all examples."""

    if os.environ.get("ANTHROPIC_API_KEY"):
        await example_anthropic()
    else:
        print("=== Anthropic Example ===")
        print("Set ANTHROPIC_API_KEY to run this example.")

    if os.environ.get("OPENAI_API_KEY"):
        await example_openai()
    else:
        print("\n=== OpenAI Example ===")
        print("Set OPENAI_API_KEY to run this example.")

    await example_openai_custom_endpoint()
    await example_custom_llm()
    await example_config_file()

    print("\n=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
