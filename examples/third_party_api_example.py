"""
Example: Third-party OpenAI-compatible API usage.

This example demonstrates how to use a third-party OpenAI-compatible API
with the Harness SDK. Just provide base_url, api_key, and model name.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from harness import AgentHarness, GlobTool, GrepTool, ReadTool


async def main():
    """Run agent with third-party OpenAI-compatible API."""

    print("=== Third-Party OpenAI-Compatible API Example ===\n")

    # Configuration
    base_url = "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2"
    api_key = "16a9dd623e0d9970b082f7d5ba01475d:YmM2NzI5M2VjOGJjNzNmYjc1N2QzNTA1"
    model = "astron-code-latest"

    # Create agent with third-party API
    agent = AgentHarness(
        base_url=base_url,
        api_key=api_key,
        model=model,
        provider="openai",
        tools=[ReadTool(), GlobTool(), GrepTool()],
    )

    print(f"Base URL: {base_url}")
    print(f"Model: {model}\n")

    # Example 1: Simple question
    print("--- Example 1: Simple Question ---")
    result = await agent.run("你好，请简单介绍一下你自己。")
    print(f"Response: {result.final_response}\n")

    # Example 2: File operations with tools
    print("--- Example 2: File Operations ---")
    result = await agent.run(
        "请用 glob 工具列出当前目录下所有的 Python 文件（*.py），"
        "然后读取 README.md 文件的前 20 行内容。"
    )
    print(f"Response: {result.final_response}\n")
    print(f"Iterations: {result.iterations}")

    # Example 3: Code analysis
    print("--- Example 3: Code Analysis ---")
    result = await agent.run(
        "用 grep 工具在 src/harness 目录下搜索 'AgentHarness' 类的定义，"
        "简要说明这个类的主要功能。"
    )
    print(f"Response: {result.final_response}\n")

    print("=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
