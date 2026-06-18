"""
测试 Circuit Breaker 是否正常工作。
"""

import asyncio
import os
import sys

sdk_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if sdk_path not in sys.path:
    sys.path.insert(0, sdk_path)

from harness import AgentHarness, ReadTool, GlobTool
from harness.types import ProgressEvent, ProgressEventType

BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
API_KEY = os.environ.get("OPENAI_API_KEY", "")
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


def on_progress(event: ProgressEvent):
    if event.type == ProgressEventType.TOOL_CALL:
        tool_name = event.data.get("tool", "unknown")
        arguments = event.data.get("arguments", {})
        print(f"  📞 {tool_name}({arguments})")
    elif event.type == ProgressEventType.CIRCUIT_BREAKER:
        print(f"  ⚠️ CIRCUIT BREAKER: {event.data}")


async def test_circuit_breaker():
    """测试 Circuit Breaker 是否在重复调用时触发"""

    agent = AgentHarness(
        base_url=BASE_URL,
        api_key=API_KEY,
        model=MODEL,
        provider="openai",
        tools=[ReadTool()],
        max_iterations=10,
    )

    # 故意让模型重复读取同一个文件
    question = "请连续读取 test.txt 文件 5 次。"

    print("=" * 60)
    print(f"问题: {question}")
    print("=" * 60)
    print()

    result = await agent.run(question, verbose=True, on_progress=on_progress)

    print()
    print("=" * 60)
    print(f"状态: {result.status.value}")
    print(f"迭代次数: {result.iterations}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_circuit_breaker())