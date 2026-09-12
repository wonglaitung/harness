"""
Multi-Agent Team 示例 — TeamOrchestrator 三种协调模式。

本示例演示：
1. Broadcast 模式：多 agent 同时分析同一任务（多视角）
2. Sequential 模式：agent 按顺序传递结论（pipeline）
3. Hierarchical 模式：leader 动态分配任务给 worker

运行方式：
    export ANTHROPIC_API_KEY=your-key-here
    python examples/multi_agent_team.py

无需真实 LLM：设置 MOCK=1 使用 mock agent 运行。
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from harness import AgentHarness
from harness.orchestrator import (
    AgentRole,
    CoordinationMode,
    TeamConfig,
    TeamOrchestrator,
)
from harness.state import create_state_store
from harness.review.queue import ReviewQueue


# ── 工具函数 ──────────────────────────────────────────────────────────────────


def create_orchestrator():
    """创建 LoopOrchestrator（真实或 mock）。"""
    from harness.orchestrator import LoopOrchestrator

    if os.environ.get("MOCK") == "1":
        from harness.testing.mock_harness import MockHarness, MockHarnessConfig

        agent = MockHarness(
            config=MockHarnessConfig(
                responses=[
                    "分析结果：代码结构清晰，模块划分合理。",
                    "Lint 结果：发现 3 个 warning，0 个 error。",
                    "审查结论：代码质量良好，建议补充单元测试。",
                ]
            )
        )
    else:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("Error: 设置 ANTHROPIC_API_KEY 或 MOCK=1")
            sys.exit(1)
        agent = AgentHarness(model="claude-sonnet-4-6")

    return LoopOrchestrator(agent=agent)


# ── 示例 1: Broadcast 模式（多视角分析） ──────────────────────────────────────


async def demo_broadcast():
    """
    Broadcast 模式：所有 agent 同时做同一件事。

    场景：三个不同角色的审查员同时审查同一段代码，
    各自从不同角度给出意见（安全性、性能、可维护性）。
    """
    print("\n" + "=" * 60)
    print("示例 1: Broadcast 模式（多视角分析）")
    print("=" * 60)

    orchestrator = create_orchestrator()
    team = TeamOrchestrator(orchestrator)

    config = TeamConfig(
        name="review-team",
        coordination_mode=CoordinationMode.BROADCAST,
        roles=[
            AgentRole(
                name="security-reviewer",
                system_prompt="你是安全审查员，专注于发现安全漏洞。",
                description="审查代码安全性",
            ),
            AgentRole(
                name="perf-reviewer",
                system_prompt="你是性能审查员，专注于发现性能问题。",
                description="审查代码性能",
            ),
            AgentRole(
                name="maint-reviewer",
                system_prompt="你是可维护性审查员，专注于代码可读性和结构。",
                description="审查代码可维护性",
            ),
        ],
    )

    team.create_team(config)
    result = await team.run(
        "review-team",
        "审查以下 Python 函数的安全性、性能和可维护性：\n\ndef process(data): return eval(data)",
    )

    print(f"\n团队结果: {'成功' if result.success else '失败'}")
    print(f"总耗时: {result.duration_seconds:.1f}s")
    for role, agent_result in result.agent_results.items():
        print(f"  [{role}] {agent_result.final_response[:80]}...")


# ── 示例 2: Sequential 模式（流水线） ────────────────────────────────────────


async def demo_sequential():
    """
    Sequential 模式：agent 按顺序传递结论。

    场景：分析 → lint → 审查，每个步骤基于前一步的结果。
    """
    print("\n" + "=" * 60)
    print("示例 2: Sequential 模式（流水线）")
    print("=" * 60)

    orchestrator = create_orchestrator()
    team = TeamOrchestrator(orchestrator)

    # 配置 SharedStateStore（黑板通信，非 P2P）
    store = create_state_store("memory")
    review_queue = ReviewQueue(human_actors={"human"})

    config = TeamConfig(
        name="pipeline",
        coordination_mode=CoordinationMode.SEQUENTIAL,
        state_store=store,          # ← 关键：通过黑板通信
        review_queue=review_queue,  # ← 失败自动升级人工
        roles=[
            AgentRole(
                name="analyzer",
                system_prompt="你是代码分析师，分析代码结构并导出关键信息。",
                description="分析代码结构",
            ),
            AgentRole(
                name="linter",
                system_prompt="你是 lint 专家，运行代码检查并导出问题列表。",
                description="运行 lint 检查",
            ),
            AgentRole(
                name="reviewer",
                system_prompt="你是代码审查员，基于分析和 lint 结果给出综合评审。",
                description="综合审查",
            ),
        ],
    )

    team.create_team(config)
    result = await team.run(
        "pipeline",
        "审查 src/auth.py 的代码质量",
    )

    print(f"\n团队结果: {'成功' if result.success else '失败'}")
    print(f"总耗时: {result.duration_seconds:.1f}s")

    # 查看黑板中的共享状态
    items = await store.list_items()
    print(f"\n黑板记录数: {len(items)}")
    for item in items:
        print(f"  [{item.source_agent}] {item.type}: {str(item.content)[:60]}...")


# ── 示例 3: Hierarchical 模式（动态分工） ────────────────────────────────────


async def demo_hierarchical():
    """
    Hierarchical 模式：leader 动态分配任务给 worker。

    场景：技术负责人分析任务后，动态决定给每个团队成员分配什么子任务。
    """
    print("\n" + "=" * 60)
    print("示例 3: Hierarchical 模式（动态分工）")
    print("=" * 60)

    orchestrator = create_orchestrator()
    team = TeamOrchestrator(orchestrator)

    config = TeamConfig(
        name="dev-team",
        coordination_mode=CoordinationMode.HIERARCHICAL,
        roles=[
            AgentRole(
                name="tech-lead",
                system_prompt="你是技术负责人，分析任务并分配给团队成员。",
                description="任务分析和分配",
            ),
            AgentRole(
                name="backend-dev",
                system_prompt="你是后端开发，专注于 API 和数据库。",
                description="后端开发",
            ),
            AgentRole(
                name="frontend-dev",
                system_prompt="你是前端开发，专注于 UI 和交互。",
                description="前端开发",
            ),
        ],
    )

    team.create_team(config)
    result = await team.run(
        "dev-team",
        "实现用户登录功能：包含 JWT 认证、密码加密、登录页面",
    )

    print(f"\n团队结果: {'成功' if result.success else '失败'}")
    print(f"总耗时: {result.duration_seconds:.1f}s")
    for role, agent_result in result.agent_results.items():
        print(f"  [{role}] {agent_result.final_response[:80]}...")


# ── 主函数 ────────────────────────────────────────────────────────────────────


async def main():
    """运行所有示例。"""
    print("Multi-Agent Team 示例")
    print("模式: MOCK=1 使用 mock agent，否则使用真实 LLM")

    await demo_broadcast()
    await demo_sequential()
    await demo_hierarchical()

    print("\n" + "=" * 60)
    print("所有示例运行完成")


if __name__ == "__main__":
    asyncio.run(main())
