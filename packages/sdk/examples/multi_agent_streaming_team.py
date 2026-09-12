"""
端到端多 Agent 流式协作示例 — Team 协调 + 流式 stream_goal() + 黑板共享状态。

把三种核心能力串起来：
1. Team 协调：多个角色（role）分工协作
2. 流式执行：每个角色的目标通过 GoalLoop.stream() 实时流式输出
   （生产环境用 AgentHarness.stream_goal()，此处用 MockStreamingAgent 替代以无需 API Key）
3. 黑板共享状态：每个角色结论写入 SharedStateStore（authoritative + provenance）

运行方式：
    python examples/multi_agent_streaming_team.py

无需真实 LLM：默认使用 MockStreamingAgent 跑通完整协作链路。
生产环境只需把 MockStreamingAgent 换成真实的 AgentHarness，
并把 `GoalLoop(agent=...).stream()` 换成 `await agent.stream_goal(goal)` 即可。
"""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from harness.loop import GoalLoop, GoalConfig, GoalStatus, VerificationMethod
from harness.loop.types import GoalResult
from harness.types import LoopResult, LoopState, TokenUsage, StreamEvent, Session
from harness.state import create_state_store


class MockStreamingAgent:
    """
    极简流式 Agent：替代真实 AgentHarness，使示例无需 API Key 即可运行。

    它实现了 GoalLoop.stream() 所需的最小接口：
    - ``stream(prompt, session_id, on_progress)`` 异步生成 StreamEvent
    - ``_loop._stream_result`` 供 GoalLoop 读取本轮 LoopResult
    - ``get_session(session_id)`` 供 GoalLoop 取会话

    生产环境替换为：
        agent = AgentHarness(model="claude-sonnet-4-6")
        async for event in agent.stream_goal(goal):
            ...
    """

    def __init__(self, role_name: str, response: str):
        self.role_name = role_name
        self._response = response
        self._loop = SimpleNamespace(_stream_result=None)
        self._session = Session(id=f"mock-{role_name}")

    async def stream(self, prompt, session_id=None, on_progress=None):
        """逐 token 模拟流式输出，最后产出 done 事件。"""
        for chunk in self._response.split(" "):
            yield StreamEvent(type="text", text=chunk + " ", source="agent", category="text")

        # 设置 LoopResult，供 GoalLoop 读取
        self._loop._stream_result = LoopResult(
            status=LoopState.COMPLETED,
            final_response=self._response,
            iterations=1,
            token_usage=TokenUsage(input_tokens=10, output_tokens=20),
            session=self._session,
        )
        yield StreamEvent(
            type="done",
            source="agent",
            category="lifecycle",
            usage=TokenUsage(input_tokens=10, output_tokens=20),
        )

    def get_session(self, session_id=None):
        return self._session


def _always_achieved(result: LoopResult) -> bool:
    """Demo 用验证器：第一轮即判定达成，使目标在 1 轮内干净结束。"""
    return True


async def run_role_goal(
    store,
    role_name: str,
    goal: str,
    response: str,
) -> GoalResult | None:
    """运行单个角色的流式目标，并将结论写入黑板（authoritative + provenance）。"""
    agent = MockStreamingAgent(role_name, response)
    config = GoalConfig(
        description=goal,
        verification_method=VerificationMethod.CUSTOM,
        custom_verifier=_always_achieved,
        max_iterations=3,
    )
    loop = GoalLoop(agent=agent, config=config)

    print(f"\n{'=' * 60}\n[角色 {role_name}] 流式目标: {goal}\n{'=' * 60}")
    async for event in loop.stream():
        if event.type == "text":
            print(event.text, end="", flush=True)
        elif event.type == "goal_iteration":
            print(f"\n  ↳ 第 {event.iteration} 轮迭代完成")
        elif event.type == "goal_verification":
            print(f"\n  ↳ 验证: {'达成' if event.achieved else '未达成'}")
        elif event.type == "goal_done":
            result = event.goal_result
            print(f"\n  ✓ 目标完成: {result.status.value}")
            # 写入黑板（authoritative 落定，必带 provenance）
            await store.put_authoritative(
                type=f"role_result:{role_name}",
                content={"goal": goal, "result": result.final_response or ""},
                source_agent=role_name,
                writer_id="harness",
                provenance=f"goal:{role_name}:{result.status.value}",
            )
            return result
    return None


async def main():
    store = create_state_store("memory")

    # Team 角色与各自目标（黑板上结构化协作，禁 P2P 传纸条）
    roles = [
        ("analyzer", "分析代码库结构", "分析完成：发现 3 个模块，依赖清晰。"),
        ("linter", "运行 lint 检查", "Lint 完成：0 error，2 warning。"),
        ("reviewer", "综合代码审查", "审查完成：代码质量评分 85/100。"),
    ]

    print("端到端多 Agent 流式协作演示")
    print("Team 协调 + 流式 stream_goal() + 黑板共享状态")

    for role, goal, resp in roles:
        await run_role_goal(store, role, goal, resp)

    # 合成阶段：读取黑板所有角色结论，流式产出最终报告
    items = await store.list_items()
    print(f"\n{'=' * 60}\n黑板汇总（{len(items)} 条角色结论）\n{'=' * 60}")
    summary_parts = []
    for it in items:
        print(f"  [{it.source_agent}] {it.content['result']}")
        summary_parts.append(f"{it.source_agent}: {it.content['result']}")

    print(f"\n{'=' * 60}\n[合成] 流式生成最终报告\n{'=' * 60}")
    synthesis = MockStreamingAgent("synthesizer", "最终报告：" + " ".join(summary_parts))
    config = GoalConfig(
        description="综合报告",
        verification_method=VerificationMethod.CUSTOM,
        custom_verifier=_always_achieved,
        max_iterations=3,
    )
    loop = GoalLoop(agent=synthesis, config=config)
    async for event in loop.stream():
        if event.type == "text":
            print(event.text, end="", flush=True)
        elif event.type == "goal_done":
            total = len(await store.list_items())
            print(f"\n\n✓ 端到端完成。黑板最终记录数: {total}")


if __name__ == "__main__":
    asyncio.run(main())
