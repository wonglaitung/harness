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

# 配置 - 使用第三方 OpenAI 兼容 API
BASE_URL = "http://47.115.141.152:8080/v2/coding"
API_KEY = "bce-v3/ALTAKSP-SVgAJ9aJuetewQXvUZLtt/608fe88fd13b29ffff4cb6aa0dfe8a6440e7e8d8"
MODEL = "glm-5"


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
    #question = "这个 harness-sdk 项目使用的包名是什么？请查看 pyproject.toml 文件"
    question = "请列出当前目录下所有的 Python 文件名称，然后读取 pyproject.toml 的前 20 行。"

    print("=" * 60)
    print(f"问题: {question}")
    print("=" * 60)
    print()

    # 运行
    result = await agent.run(question, verbose=True)

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

    print(f"\n响应内容:\n{result.content[:500]}...")


if __name__ == "__main__":
    asyncio.run(test_demo())
