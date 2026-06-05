"""
单独测试演示 2：验证模型能在获取信息后正确停止。

测试场景：让模型查找 harness-sdk 的包名
预期结果：
- 模型调用 glob + read 获取信息
- 模型在获得答案后立即停止（低迭代次数）
- 不触发 circuit breaker

运行方式:
    cd /data/harness/packages/sdk
    PYTHONPATH=src python examples/demo2_test.py
"""

import asyncio
import os
import sys

# 确保 SDK 在路径中
sdk_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if sdk_path not in sys.path:
    sys.path.insert(0, sdk_path)

from harness import AgentHarness, ReadTool, GlobTool
from harness.types import ProgressEvent, ProgressEventType

# 配置 - 使用第三方 OpenAI 兼容 API
BASE_URL = "http://47.115.141.152:8080/v2/coding"
API_KEY = "bce-v3/ALTAKSP-SVgAJ9aJuetewQXvUZLtt/608fe88fd13b29ffff4cb6aa0dfe8a6440e7e8d8"
MODEL = "glm-5.1"


def on_progress(event: ProgressEvent):
    """打印工具调用详情"""
    if event.type == ProgressEventType.TOOL_CALL:
        tool_name = event.data.get("tool", "unknown")
        arguments = event.data.get("arguments", {})
        print(f"  📞 工具调用: {tool_name}")
        print(f"     参数: {arguments}")
    elif event.type == ProgressEventType.TOOL_RESULT:
        tool_name = event.data.get("tool", "unknown")
        success = event.data.get("success", False)
        content_preview = event.data.get("content", "")[:100]
        print(f"  📥 工具结果: {tool_name} (success={success})")
        print(f"     内容预览: {content_preview}...")


async def test_demo():
    """测试模型是否能正确停止"""

    # 创建 Agent
    agent = AgentHarness(
        base_url=BASE_URL,
        api_key=API_KEY,
        model=MODEL,
        provider="openai",
        tools=[ReadTool(), GlobTool()],
        max_iterations=10,
    )

    # 问题 - 需要查找信息
    question = "请执行以下两个操作：\n1. 使用 glob 工具列出当前目录下所有的 *.py 文件\n2. 使用 read 工具读取 pyproject.toml 文件的全部内容\n\n完成后直接展示结果，不要做额外操作。"

    print("=" * 60)
    print(f"问题: {question}")
    print("=" * 60)
    print()

    # 运行，带进度回调
    result = await agent.run(question, verbose=True, on_progress=on_progress)

    print()
    print("=" * 60)
    print("结果统计:")
    print(f"  状态: {result.status.value}")
    print(f"  迭代次数: {result.iterations}")
    print(f"  Token 使用: {result.token_usage}")
    print("=" * 60)

    # 判断是否成功
    if result.iterations <= 2:
        print("\n✅ 测试通过: 模型在获取信息后正确停止")
    elif result.iterations >= 5:
        print("\n❌ 测试失败: 模型进行了过多迭代")
    else:
        print(f"\n⚠️ 需要关注: 迭代次数为 {result.iterations}")

    print(f"\n响应内容:\n{result.content[:1000]}...")


if __name__ == "__main__":
    asyncio.run(test_demo())