"""
Test script for custom API configuration.

This demonstrates using the Harness SDK with a custom OpenAI-compatible API.

Usage:
    PYTHONPATH=packages/sdk/src python examples/test_custom_api.py
"""

import asyncio
from harness import AgentHarness
from harness.sdk.config import HarnessConfig


# Custom API configuration
# Provided by user
CUSTOM_API = {
    "base_url": "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2",
    "api_key": "16a9dd623e0d9970b082f7d5ba01475d:YmM2NzI5M2VjOGJjNzNmYjc1N2QzNTA1",
    "model": "xopglm5",
    "provider": "openai",  # Use OpenAI-compatible mode
}


async def test_custom_api():
    """Test agent with custom API."""
    print(f"Testing custom API: {CUSTOM_API['base_url']}")
    print(f"Model: {CUSTOM_API['model']}")
    print("-" * 50)

    # Create config for custom API
    config = HarnessConfig.from_custom_api(
        api_key=CUSTOM_API["api_key"],
        base_url=CUSTOM_API["base_url"],
        model=CUSTOM_API["model"],
        provider=CUSTOM_API["provider"],
        max_iterations=5,
    )

    # Create agent
    agent = AgentHarness(config=config)

    # Test simple query
    print("Sending: 'Hello, can you introduce yourself briefly?'")
    print("-" * 50)

    try:
        result = await agent.run(prompt="Hello, can you introduce yourself briefly?")

        print(f"Status: {result.status.value}")
        print(f"Iterations: {result.iterations}")
        print(f"Tokens: {result.token_usage.input_tokens} in / {result.token_usage.output_tokens} out")
        print("-" * 50)
        print(f"Response:\n{result.content}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_custom_api())
