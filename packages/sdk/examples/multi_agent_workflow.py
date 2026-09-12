"""
Multi-Agent Workflow 示例 — WorkflowEngine 步骤间黑板通信。

本示例演示：
1. DAG 步骤定义（并行 + 串行）
2. 模板变量传递（{{step.exports.key}}）
3. 失败重试 + ReviewQueue 升级
4. 执行前死锁检测

运行方式：
    export ANTHROPIC_API_KEY=your-key-here
    python examples/multi_agent_workflow.py

无需真实 LLM：设置 MOCK=1 使用 mock agent 运行。
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from harness import AgentHarness
from harness.orchestrator import (
    ExecutionMode,
    LoopOrchestrator,
    WorkflowConfig,
    WorkflowEngine,
    WorkflowStep,
)
from harness.state import create_state_store
from harness.review.queue import ReviewQueue


# ── 工具函数 ──────────────────────────────────────────────────────────────────


def create_orchestrator():
    """创建 LoopOrchestrator（真实或 mock）。"""
    if os.environ.get("MOCK") == "1":
        from harness.testing.mock_harness import MockHarness, MockHarnessConfig

        agent = MockHarness(
            config=MockHarnessConfig(
                responses=[
                    "分析完成：发现 3 个模块，依赖关系清晰。",
                    "Lint 完成：0 error, 2 warning。",
                    "安全扫描完成：无高危漏洞。",
                    "综合审查完成：代码质量评分 85/100。",
                    "报告已生成：摘要 + 详细问题列表。",
                ]
            )
        )
    else:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("Error: 设置 ANTHROPIC_API_KEY 或 MOCK=1")
            sys.exit(1)
        agent = AgentHarness(model="claude-sonnet-4-6")

    return LoopOrchestrator(agent=agent)


# ── 示例 1: 基础流水线（并行 + 串行） ────────────────────────────────────────


async def demo_basic_pipeline():
    """
    基础流水线：analyze 和 lint 并行，review 等两者完成后串行。

    DAG 结构：
        analyze ──┐
                   ├──→ review → report
        lint    ──┘
    """
    print("\n" + "=" * 60)
    print("示例 1: 基础流水线（并行 + 串行）")
    print("=" * 60)

    orchestrator = create_orchestrator()
    review_queue = ReviewQueue(human_actors={"human"})
    engine = WorkflowEngine(orchestrator, review_queue=review_queue)

    workflow = WorkflowConfig(
        name="code-review-pipeline",
        max_parallel_steps=2,
        steps=[
            WorkflowStep(
                name="analyze",
                goal="分析 src/ 的代码结构，识别主要模块和依赖关系",
                mode=ExecutionMode.PARALLEL,
            ),
            WorkflowStep(
                name="lint",
                goal="运行 ruff check src/，统计 error 和 warning 数量",
                mode=ExecutionMode.PARALLEL,
            ),
            WorkflowStep(
                name="review",
                goal="基于分析结果和 lint 结果，给出综合代码审查意见",
                depends_on=["analyze", "lint"],
            ),
            WorkflowStep(
                name="report",
                goal="生成最终审查报告，包含问题摘要和改进建议",
                depends_on=["review"],
            ),
        ],
    )

    result = await engine.run(workflow)

    print(f"\n工作流状态: {result.status.value}")
    for name, step in result.steps.items():
        status = "✓" if step.status.value == "success" else "✗"
        print(f"  {status} {name}: {step.status.value}")


# ── 示例 2: 模板变量传递 ─────────────────────────────────────────────────────


async def demo_template_passing():
    """
    模板变量：步骤 B 通过 {{collect.exports.key}} 读取步骤 A 的输出。

    这不是 P2P 传纸条，而是从 WorkflowResult 上下文渲染结构化数据。
    """
    print("\n" + "=" * 60)
    print("示例 2: 模板变量传递（上下文渲染）")
    print("=" * 60)

    orchestrator = create_orchestrator()
    review_queue = ReviewQueue(human_actors={"human"})
    engine = WorkflowEngine(orchestrator, review_queue=review_queue)

    workflow = WorkflowConfig(
        name="template-demo",
        steps=[
            WorkflowStep(
                name="collect",
                goal="收集用户需求，导出功能列表和优先级",
            ),
            WorkflowStep(
                name="plan",
                goal="基于需求列表制定开发计划",
                depends_on=["collect"],
            ),
            WorkflowStep(
                name="execute",
                goal="按计划执行开发任务",
                depends_on=["plan"],
            ),
        ],
    )

    result = await engine.run(workflow)

    print(f"\n工作流状态: {result.status.value}")
    for name, step in result.steps.items():
        status = "✓" if step.status.value == "success" else "✗"
        print(f"  {status} {name}: {step.status.value}")


# ── 示例 3: 失败重试 + ReviewQueue 升级 ──────────────────────────────────────


async def demo_failure_handling():
    """
    失败场景：步骤失败后自动重试，仍失败则升级 ReviewQueue 供人工处理。
    """
    print("\n" + "=" * 60)
    print("示例 3: 失败重试 + ReviewQueue 升级")
    print("=" * 60)

    orchestrator = create_orchestrator()
    review_queue = ReviewQueue(human_actors={"human"})
    engine = WorkflowEngine(orchestrator, review_queue=review_queue)

    workflow = WorkflowConfig(
        name="failure-demo",
        steps=[
            WorkflowStep(name="step-ok", goal="正常执行的步骤"),
            WorkflowStep(
                name="step-fail",
                goal="这个步骤会失败",
                depends_on=["step-ok"],
                max_retries=2,  # 最多重试 2 次
            ),
            WorkflowStep(
                name="step-after-fail",
                goal="依赖失败步骤的下游",
                depends_on=["step-fail"],
            ),
        ],
    )

    result = await engine.run(workflow)

    print(f"\n工作流状态: {result.status.value}")
    for name, step in result.steps.items():
        status = "✓" if step.status.value == "success" else "✗"
        error = f" ({step.error})" if step.error else ""
        print(f"  {status} {name}: {step.status.value}{error}")

    # 查看 ReviewQueue
    pending = review_queue.pending()
    print(f"\nReviewQueue 待审项: {len(pending)}")
    for item in pending:
        print(f"  - {item.source}: {item.content[:60] if item.content else ''}...")


# ── 示例 4: 死锁检测 ────────────────────────────────────────────────────────


async def demo_deadlock_detection():
    """
    死锁检测：循环依赖在执行前就被拒绝，不浪费任何 agent 调用。
    """
    print("\n" + "=" * 60)
    print("示例 4: 死锁检测")
    print("=" * 60)

    orchestrator = create_orchestrator()
    review_queue = ReviewQueue(human_actors={"human"})
    engine = WorkflowEngine(orchestrator, review_queue=review_queue)

    workflow = WorkflowConfig(
        name="cyclic-workflow",
        steps=[
            WorkflowStep(name="A", goal="步骤 A", depends_on=["B"]),  # A 依赖 B
            WorkflowStep(name="B", goal="步骤 B", depends_on=["A"]),  # B 依赖 A → 循环！
        ],
    )

    result = await engine.run(workflow)

    print(f"\n工作流状态: {result.status.value}")
    print(f"错误信息: {result.error}")
    print("→ 循环依赖在执行前就被检测到，没有浪费任何 agent 调用")


# ── 主函数 ────────────────────────────────────────────────────────────────────


async def main():
    """运行所有示例。"""
    print("Multi-Agent Workflow 示例")
    print("模式: MOCK=1 使用 mock agent，否则使用真实 LLM")

    await demo_basic_pipeline()
    await demo_template_passing()
    await demo_failure_handling()
    await demo_deadlock_detection()

    print("\n" + "=" * 60)
    print("所有示例运行完成")


if __name__ == "__main__":
    asyncio.run(main())
