"""治理手工演练入口（设计稿 §7 / §8 / §10 / §11 的可操作验证）。

用法::

    cd packages/sdk/examples/governance_playground
    python run.py happy
    python run.py skip
    python run.py constraint
    python run.py approval          # 另一个终端执行 README 里的 approve 命令
    AML_NO_OUTPUT=1 python run.py missing_output

脚本会把 ``skills/`` 复制到 ``.work/.harness/skills``，并在 ``.work`` 下隔离
CWD 与 HOME——**不会读写你的 ~/.harness**。这不只是整洁问题：技能加载器只读
``~/.harness/skills`` 与 ``./.harness/skills``（导入时求值），所以必须先切
CWD 再导入 harness。同理 ``HOME`` 要在导入前设置。
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
WORK = BASE / ".work"
HOME = WORK / "home"

SCENARIOS = ("happy", "skip", "constraint", "approval", "missing_output")

AGENTS = {
    "happy": "report-assembler",
    "skip": "report-assembler",
    "missing_output": "report-assembler",
    "constraint": "payment-agent",
    "approval": "payment-agent",
}


def _prepare_workspace() -> None:
    """准备隔离的工作区：复制技能 + 切 CWD + 切 HOME（必须在导入 harness 前）。"""
    skills_dir = WORK / ".harness" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    HOME.mkdir(parents=True, exist_ok=True)
    for source in sorted((BASE / "skills").glob("*.md")):
        shutil.copy2(source, skills_dir / source.name)
    os.chdir(WORK)
    os.environ["HOME"] = str(HOME)


def _build_responses(scenario: str) -> list:
    """按场景构造 Mock LLM 的响应序列（不联网）。"""
    from harness.llm.mock import MockResponse
    from harness.types import StopReason

    def call(name: str, args: dict | None = None, rid: str = "c1") -> MockResponse:
        return MockResponse(
            content="",
            tool_calls=[{"id": rid, "name": name, "arguments": args or {}}],
            stop_reason=StopReason.TOOL_USE,
        )

    if scenario == "happy":
        return [
            call("core_banking_api:read_only", rid="c1"),
            call("aml_screening:run", rid="c2"),
            call("report_writer:draft", rid="c3"),
            MockResponse(content="报告草稿已生成。"),
        ]
    if scenario == "skip":
        return [
            # 跳步：collect_data / aml_check 未做，直接出报告
            call("report_writer:draft", rid="c1"),
            MockResponse(content="收到拒绝，停止。"),
        ]
    if scenario == "constraint":
        return [
            call("pay:transfer", {"amount": 9_999_999}, rid="c1"),  # 超金额上限
            MockResponse(content="收到拒绝，停止。"),
        ]
    if scenario == "approval":
        return [
            call("pay:transfer", {"amount": 100}, rid="c1"),  # payment 强制审批
            MockResponse(content="审批通过后完成。"),
        ]
    # missing_output
    return [
        call("core_banking_api:read_only", rid="c1"),
        call("aml_screening:run", rid="c2"),  # 配 AML_NO_OUTPUT=1 时不产出 aml_hit
        call("report_writer:draft", rid="c3"),
        MockResponse(content="停止。"),
    ]


def _make_tools():
    """构造演练用工具（strict 下必须声明 capability / idempotent）。"""
    from harness.tools.base import Tool
    from harness.types import ToolResult

    class Read(Tool):
        capability = "read"
        idempotent = True

        @property
        def name(self) -> str:
            return "core_banking_api:read_only"

        @property
        def description(self) -> str:
            return "读取核心系统（演练桩）"

        async def execute(self, arguments, context) -> ToolResult:
            print("  [tool] core_banking_api:read_only")
            return ToolResult(tool_call_id="", success=True, content="ok")

    class Aml(Tool):
        capability = "write"
        idempotent = True

        @property
        def name(self) -> str:
            return "aml_screening:run"

        @property
        def description(self) -> str:
            return "AML 筛查（演练桩）"

        async def execute(self, arguments, context) -> ToolResult:
            print("  [tool] aml_screening:run")
            metadata = (
                {}
                if os.getenv("AML_NO_OUTPUT")
                else {"aml_hit": os.getenv("AML_HIT", "false")}
            )
            return ToolResult(
                tool_call_id="", success=True, content="ok", metadata=metadata
            )

    class Draft(Tool):
        capability = "write"
        idempotent = False

        @property
        def name(self) -> str:
            return "report_writer:draft"

        @property
        def description(self) -> str:
            return "生成报告草稿（演练桩）"

        async def execute(self, arguments, context) -> ToolResult:
            print("  [tool] report_writer:draft")
            return ToolResult(tool_call_id="", success=True, content="draft ok")

    class Pay(Tool):
        capability = "payment"
        idempotent = False

        @property
        def name(self) -> str:
            return "pay:transfer"

        @property
        def description(self) -> str:
            return "转账（演练桩）"

        async def execute(self, arguments, context) -> ToolResult:
            print(f"  [tool] pay:transfer amount={arguments.get('amount')}")
            return ToolResult(tool_call_id="", success=True, content="paid")

    return Read(), Aml(), Draft(), Pay()


async def main() -> None:
    scenario = sys.argv[1] if len(sys.argv) > 1 else "happy"
    if scenario not in SCENARIOS:
        raise SystemExit(f"未知场景 {scenario}；可选：{list(SCENARIOS)}")

    _prepare_workspace()

    from harness.llm.mock import MockLLMClient
    from harness.sdk.config import HarnessConfig
    from harness.sdk.harness import AgentHarness

    harness = AgentHarness(
        config=HarnessConfig(
            model="mock-model",
            strict=True,
            governance_agent_id=AGENTS[scenario],
            sandbox_workspace=os.getcwd(),
        ),
        llm_client=MockLLMClient(responses=_build_responses(scenario)),
    )
    for tool in _make_tools():
        harness.register_tool(tool)

    policy = harness.governance_policy()
    print(
        f"治理策略：agent_id={policy.agent_id} "
        f"tools={sorted(policy.tool_names)} "
        f"steps={[s.id for s in policy.workflow.steps]} "
        f"material={policy.material}"
    )
    print()
    print(f"提示：同一工作区的 CLI 需带 HOME={HOME}")
    print(f"      例：HOME={HOME} python -m harness.cli governance status {policy.agent_id}")
    print()
    print(f"=== 场景：{scenario} ===")

    result = await harness.run("组装信贷报告", session_id="s1")

    print()
    print(f"run 结论：{result.status.value}")
    if result.error:
        print(f"错误：{result.error}")
    print(f"最终回答：{result.final_response!r}")
    print()
    print(f"事件日志：{HOME}/.harness/audit/governance/<日期>/<pid>.jsonl")
    print(f"审批目录：{HOME}/.harness/control/approvals/")
    print(f"控制状态：{HOME}/.harness/control/{policy.agent_id}.json")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
