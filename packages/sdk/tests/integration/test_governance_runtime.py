"""治理运行期行为：Kill Switch 检查点、token 限额、INCOMPLETE 结论。

覆盖设计稿 §10.3（检查点）、§9.1（token 限额）、§8.3（run 结论 INCOMPLETE）。
"""

from __future__ import annotations

import types

import yaml

from harness.core.agent_loop import AgentLoop
from harness.governance.control import ControlPlane
from harness.governance.events import GovernanceEventLog
from harness.governance.gateway import GovernanceGateway
from harness.governance.policy import compile_policy
from harness.governance.schema import parse_governance_block
from harness.llm.mock import MockLLMClient, MockResponse
from harness.memory.session import Session
from harness.tools.base import Tool
from harness.tools.executor import ExecutorConfig, ToolExecutor
from harness.tools.registry import ToolRegistry
from harness.types import LoopResult, LoopState, ToolCall, ToolResult

BLOCK = {
    "agent_id": "credit-paper-assembler",
    "version": "1.2.0",
    "approved_by": "PR #1284",
    "business_intent": "组装信贷报告初稿",
    "owners": {"accountable": "Head of Credit Risk", "technical": "DevOps Lead A"},
    "material": True,
    "tools": [
        {"name": "core_banking_api:read_only", "capability": "read", "idempotent": True},
        {"name": "aml_screening:run", "capability": "write", "idempotent": True},
    ],
    "workflow": {
        "steps": [
            {"id": "collect_data", "tools": ["core_banking_api:read_only"]},
            {"id": "aml_check", "tools": ["aml_screening:run"]},
        ]
    },
    "limits": {
        "max_tool_calls_per_run": 50,
        "max_calls_per_minute": 20,
        "max_tokens_per_run": 200000,
    },
}


class _Context:
    def build(self, session):
        return types.SimpleNamespace(
            messages=session.messages, system_prompt=""
        )


class _Read(Tool):
    capability = "read"
    idempotent = True

    def __init__(self):
        self.calls = 0

    @property
    def name(self):
        return "core_banking_api:read_only"

    @property
    def description(self):
        return "read"

    async def execute(self, arguments, context):
        self.calls += 1
        return ToolResult(tool_call_id="", success=True, content="ok")


class _Aml(Tool):
    capability = "write"
    idempotent = True

    @property
    def name(self):
        return "aml_screening:run"

    @property
    def description(self):
        return "aml"

    async def execute(self, arguments, context):
        return ToolResult(
            tool_call_id="", success=True, content="ok", metadata={"aml_hit": "false"}
        )


def _gateway(tmp_path, **overrides):
    raw = yaml.safe_load(yaml.safe_dump(BLOCK))
    raw.update(overrides.pop("block", {}))
    policy = compile_policy([parse_governance_block(raw)])
    control = ControlPlane(directory=tmp_path / "control")
    log = GovernanceEventLog(directory=tmp_path / "audit")
    return GovernanceGateway(policy, control=control, event_log=log, **overrides)


def _loop(gateway, responses=None, read=None, registry=None):
    if registry is None:
        registry = ToolRegistry()
        registry.register(read or _Read())
        registry.register(_Aml())
    executor = ToolExecutor(registry, ExecutorConfig(timeout=5))
    executor.governance = gateway
    loop = AgentLoop(
        llm_client=MockLLMClient(responses=responses or [MockResponse(content="done")]),
        tool_executor=executor,
        context_builder=_Context(),
        session_manager=object(),
        config=None,
    )
    loop.governance_gateway = gateway
    return loop


# --------------------------------------------------------------------------
# Kill Switch 检查点（§10.3）
# --------------------------------------------------------------------------


async def test_run_start_checkpoint_blocks_without_llm(tmp_path):
    """suspended → run 开始即 INTERRUPTED，**不调用 LLM**。"""
    gateway = _gateway(tmp_path)
    gateway.control.suspend("credit-paper-assembler", reason="AML 被跳过")
    llm = MockLLMClient(responses=[MockResponse(content="should-not-run")])
    loop = _loop(gateway)
    loop.llm = llm

    result = await loop.run("hi", Session(id="s1"))

    assert result.status == LoopState.INTERRUPTED
    assert "Kill Switch" in (result.error or "")
    assert llm._call_count == 0


async def test_tool_completion_checkpoint_stops_remaining(tmp_path):
    """工具执行后被 suspend → 剩余工具不再执行（§10.3 第 4 个检查点）。"""
    gateway = _gateway(tmp_path)
    loop = _loop(gateway)
    loop.governance_context = gateway.new_context()
    session = Session(id="s1")

    class _SuspendingRead(_Read):
        async def execute(self, arguments, context):
            result = await super().execute(arguments, context)
            gateway.control.suspend("credit-paper-assembler", reason="during run")
            return result

    # 第一个工具执行完成后 suspend，第二个工具应被 Kill Switch 拒绝
    read = _SuspendingRead()
    registry = ToolRegistry()
    registry.register(read)
    loop.tools = ToolExecutor(registry, ExecutorConfig(timeout=5))
    loop.tools.governance = gateway

    results = await loop._execute_tools(
        [
            ToolCall(id="1", name="core_banking_api:read_only", arguments={}),
            ToolCall(id="2", name="core_banking_api:read_only", arguments={}),
        ],
        session,
    )
    # 第一个放行；suspend 在第一个结果之后被检查
    assert len(results) == 2
    assert read.calls == 1, "suspend 之后不得继续执行工具"
    assert "Kill Switch" in (results[1].error or "")


# --------------------------------------------------------------------------
# token 限额（§9.1）
# --------------------------------------------------------------------------


async def test_token_limit_stops_run(tmp_path):
    gateway = _gateway(tmp_path, block={"limits": {
        "max_tool_calls_per_run": 50,
        "max_calls_per_minute": 20,
        "max_tokens_per_run": 1,
    }})
    loop = _loop(gateway)
    result = await loop.run("hi", Session(id="s1"))
    assert result.status == LoopState.ERROR
    assert "token" in (result.error or "")


# --------------------------------------------------------------------------
# run 结论 INCOMPLETE（§8.3）
# --------------------------------------------------------------------------


async def test_terminal_step_skipped_marks_incomplete(tmp_path):
    gateway = _gateway(tmp_path)
    loop = _loop(gateway)
    ctx = gateway.new_context()
    loop.governance_context = ctx
    # 手动把末端 step 置为 skipped（等价于 if 不成立）
    ctx.step_state("aml_check").outcome = "skipped"
    result = loop._finalize_governance_result(
        LoopResult(status=LoopState.COMPLETED, session=Session(id="s1"))
    )
    assert result.status == LoopState.INCOMPLETE


async def test_completed_run_without_skip_stays_completed(tmp_path):
    gateway = _gateway(tmp_path)
    loop = _loop(gateway)
    loop.governance_context = gateway.new_context()
    result = loop._finalize_governance_result(
        LoopResult(status=LoopState.COMPLETED, session=Session(id="s1"))
    )
    assert result.status == LoopState.COMPLETED
