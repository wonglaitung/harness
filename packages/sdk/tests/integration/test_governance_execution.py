"""治理网关接入执行路径的集成测试（设计稿 §7.1 / §7.2）。

验证：
- 治理判定在 `ToolExecutor` 内（**单入口**），拒绝的工具**根本没被执行**
- 缺少运行上下文 → fail-closed
- 放行后执行结果回写事件与 step 状态
- `AgentHarness` 把网关装配到 loop 与 executor
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from harness.governance.events import GovernanceEventLog
from harness.governance.gateway import GovernanceGateway
from harness.governance.policy import compile_policy
from harness.governance.schema import parse_governance_block
from harness.sdk.config import HarnessConfig
from harness.sdk.harness import AgentHarness
from harness.tools.base import Tool, ToolContext
from harness.tools.executor import ExecutorConfig, ToolExecutor
from harness.tools.permissions import PermissionSet
from harness.tools.registry import ToolRegistry
from harness.types import ToolCall, ToolResult

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


class _Read(Tool):
    capability = "read"
    idempotent = True

    def __init__(self) -> None:
        self.calls: list[dict] = []

    @property
    def name(self) -> str:
        return "core_banking_api:read_only"

    @property
    def description(self) -> str:
        return "read"

    async def execute(self, arguments, context) -> ToolResult:
        self.calls.append(arguments)
        return ToolResult(tool_call_id="", success=True, content="ok")


class _Aml(Tool):
    capability = "write"
    idempotent = True

    def __init__(self) -> None:
        self.calls: list[dict] = []

    @property
    def name(self) -> str:
        return "aml_screening:run"

    @property
    def description(self) -> str:
        return "aml"

    async def execute(self, arguments, context) -> ToolResult:
        self.calls.append(arguments)
        return ToolResult(
            tool_call_id="", success=True, content="ok", metadata={"aml_hit": "false"}
        )


@pytest.fixture
def policy():
    return compile_policy(
        [parse_governance_block(yaml.safe_load(yaml.safe_dump(BLOCK)))]
    )


@pytest.fixture
def executor(policy, tmp_path):
    registry = ToolRegistry()
    read_tool = _Read()
    registry.register(read_tool)
    executor = ToolExecutor(registry, ExecutorConfig(timeout=5))
    event_log = GovernanceEventLog(directory=tmp_path / "audit")
    gateway = GovernanceGateway(policy, event_log=event_log)
    executor.governance = gateway
    executor.read_tool = read_tool  # type: ignore[attr-defined]
    executor.gateway = gateway  # type: ignore[attr-defined]
    executor.event_log = event_log  # type: ignore[attr-defined]
    return executor


def _context(executor, ctx=None):
    return ToolContext(
        session_id="s1",
        working_directory=Path("/tmp"),
        permissions=PermissionSet.full_access(),
        metadata={"governance_context": ctx} if ctx is not None else {},
    )


async def test_denied_tool_is_not_executed(executor):
    """白名单外的工具：判定拒绝 → 工具**没有**被执行。"""
    ctx = executor.gateway.new_context()
    result = await executor.execute(
        ToolCall(id="1", name="unknown_tool", arguments={}), _context(executor, ctx)
    )
    assert result.success is False
    assert "治理网关拒绝" in (result.error or "")
    assert executor.read_tool.calls == []


async def test_missing_run_context_is_fail_closed(executor):
    """治理开启但上下文缺失 → 拒绝（不放行）。"""
    result = await executor.execute(
        ToolCall(id="1", name="core_banking_api:read_only", arguments={}),
        _context(executor, None),
    )
    assert result.success is False
    assert "缺少运行上下文" in (result.error or "")
    assert executor.read_tool.calls == []


async def test_allowed_tool_executes_and_records_result(executor):
    ctx = executor.gateway.new_context(run_id="run-1")
    result = await executor.execute(
        ToolCall(id="1", name="core_banking_api:read_only", arguments={}),
        _context(executor, ctx),
    )
    assert result.success is True
    assert len(executor.read_tool.calls) == 1

    path = next(executor.event_log.directory.rglob("*.jsonl"))
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    kinds = [e["event"] for e in events]
    assert "tool_call_decision" in kinds
    assert "tool_call_result" in kinds
    # 步骤结论在游标推进时确定（pull 模型，§8.3）
    assert ctx.step_state("collect_data").tools_succeeded
    ctx.advance_cursor()
    assert ctx.step_state("collect_data").outcome == "success"


async def test_step_order_is_enforced_by_executor(executor):
    """跳步：未完成 collect_data 就调用 aml_screening:run → 拒绝。"""
    ctx = executor.gateway.new_context()
    result = await executor.execute(
        ToolCall(id="1", name="aml_screening:run", arguments={}),
        _context(executor, ctx),
    )
    assert result.success is False
    assert "跳步" in (result.error or "")


async def test_unregistered_tool_rejected_by_governance(executor):
    """治理开启时，未登记工具由白名单判定拒绝（§7.2 第 2 步）。"""
    ctx = executor.gateway.new_context()
    result = await executor.execute(
        ToolCall(id="1", name="not_registered", arguments={}), _context(executor, ctx)
    )
    assert result.success is False
    assert "治理网关拒绝" in (result.error or "")
    assert "白名单" in (result.error or "")


async def test_unknown_tool_without_governance_reports_unknown():
    """治理未开启：保持原有"未知工具"语义（零迁移）。"""
    registry = ToolRegistry()
    executor = ToolExecutor(registry, ExecutorConfig(timeout=5))
    result = await executor.execute(
        ToolCall(id="1", name="not_registered", arguments={}),
        ToolContext(
            session_id="s1",
            working_directory=Path("/tmp"),
            permissions=PermissionSet.full_access(),
        ),
    )
    assert result.success is False
    assert "Unknown tool" in (result.error or "")


# --------------------------------------------------------------------------
# AgentHarness 装配
# --------------------------------------------------------------------------

SKILL_WITH_GOVERNANCE = """---
name: credit-paper-assembler
description: 组装信贷报告初稿
tools:
  allowed: [core_banking_api:read_only, aml_screening:run]
governance:
  agent_id: credit-paper-assembler
  version: 1.2.0
  approved_by: "PR #1284"
  business_intent: 组装信贷报告初稿供信用分析师复核
  owners:
    accountable: Head of Credit Risk
    technical: DevOps Lead A
  material: true
  tools:
    - name: core_banking_api:read_only
      capability: read
      idempotent: true
    - name: aml_screening:run
      capability: write
      idempotent: true
  workflow:
    steps:
      - id: collect_data
        tools: [core_banking_api:read_only]
      - id: aml_check
        tools: [aml_screening:run]
  limits:
    max_tool_calls_per_run: 50
    max_calls_per_minute: 20
    max_tokens_per_run: 200000
---

正文
"""


def test_harness_wires_gateway_into_loop_and_executor(tmp_path, monkeypatch):
    from harness.skills import loader

    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "governed.md").write_text(SKILL_WITH_GOVERNANCE, encoding="utf-8")
    monkeypatch.setattr(loader, "DEFAULT_SKILL_PATHS", [skills])

    harness = AgentHarness(
        config=HarnessConfig(
            api_key="test-key",
            model="mock-model",
            strict=True,
            governance_agent_id="credit-paper-assembler",
        )
    )
    harness.register_tool(_Read())
    harness.register_tool(_Aml())

    gateway = harness.governance_gateway()
    assert gateway is not None
    assert harness._loop.governance_gateway is gateway
    assert harness._tool_executor.governance is gateway

    # 每个 run 重建运行上下文（§4.4）
    ctx = gateway.new_context()
    assert ctx.run_id != gateway.new_context().run_id


def test_register_tool_without_declaration_rejected_in_strict(tmp_path, monkeypatch):
    """strict 下未声明 capability 的工具 → 拒绝注册（§7.3）。"""
    from harness.skills import loader
    from harness.tools.base import Tool

    class _Undeclared(Tool):
        @property
        def name(self):
            return "undeclared_tool"

        @property
        def description(self):
            return "no governance declaration"

        async def execute(self, arguments, context):
            return ToolResult(tool_call_id="", success=True, content="ok")

    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "governed.md").write_text(SKILL_WITH_GOVERNANCE, encoding="utf-8")
    monkeypatch.setattr(loader, "DEFAULT_SKILL_PATHS", [skills])

    harness = AgentHarness(
        config=HarnessConfig(
            api_key="test-key",
            model="mock-model",
            strict=True,
            governance_agent_id="credit-paper-assembler",
        )
    )
    with pytest.raises(ValueError, match="capability"):
        harness.register_tool(_Undeclared())


def test_declaration_conflict_with_block_rejected(tmp_path, monkeypatch):
    """代码声明与治理块声明冲突 → 编译期拒绝（§7.3 / §6.4.2）。"""
    from harness.skills import loader

    class _Conflicting(_Read):
        capability = "write"  # 治理块里是 read

    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "governed.md").write_text(SKILL_WITH_GOVERNANCE, encoding="utf-8")
    monkeypatch.setattr(loader, "DEFAULT_SKILL_PATHS", [skills])

    harness = AgentHarness(
        config=HarnessConfig(
            api_key="test-key",
            model="mock-model",
            strict=True,
            governance_agent_id="credit-paper-assembler",
        )
    )
    harness.register_tool(_Conflicting())
    harness.register_tool(_Aml())
    with pytest.raises(RuntimeError, match="治理声明冲突"):
        harness.governance_policy()


# --------------------------------------------------------------------------
# Hook 改写参数后，仍以**终态参数**校验（P0-2 验收条款）
# --------------------------------------------------------------------------

CONSTRAINT_BLOCK = {
    "agent_id": "loan-agent",
    "version": "1.0.0",
    "approved_by": "PR #1",
    "business_intent": "放款",
    "owners": {"accountable": "Head of Credit", "technical": "DevOps"},
    "material": True,
    "tools": [
        {
            "name": "loan:disburse",
            "capability": "write",
            "idempotent": False,
            "constraints": {
                "required_fields": ["amount"],
                "amount_field": "amount",
                "max_amount": 1_000_000,
            },
        }
    ],
    "workflow": {"steps": [{"id": "disburse", "tools": ["loan:disburse"]}]},
    "limits": {
        "max_tool_calls_per_run": 10,
        "max_calls_per_minute": 10,
        "max_tokens_per_run": 1000,
    },
}


class _Disburse(Tool):
    capability = "write"
    idempotent = False
    constraints = {"amount_field": "amount", "max_amount": 1_000_000}

    def __init__(self) -> None:
        self.calls: list[dict] = []

    @property
    def name(self) -> str:
        return "loan:disburse"

    @property
    def description(self) -> str:
        return "disburse"

    async def execute(self, arguments, context) -> ToolResult:
        self.calls.append(arguments)
        return ToolResult(tool_call_id="", success=True, content="ok")


class _RewriteAmountHook:
    """把金额改写成超限值——模拟 Hook 的 MODIFY_ARGS。"""

    @property
    def hook_points(self):
        from harness.types import HookPoint

        return [HookPoint.BEFORE_TOOL_EXECUTE]

    async def execute(self, context):
        from harness.types import HookResult

        return HookResult.modify_args({"amount": 9_999_999})


async def test_hook_modified_args_validated_at_final_state(tmp_path):
    """Hook 改写参数后，网关校验的是**改写后的终态**，不是原始参数。"""
    import types

    from harness.core.agent_loop import AgentLoop
    from harness.governance.gateway import GovernanceGateway
    from harness.governance.policy import compile_policy
    from harness.governance.schema import parse_governance_block

    policy = compile_policy(
        [parse_governance_block(yaml.safe_load(yaml.safe_dump(CONSTRAINT_BLOCK)))]
    )
    registry = ToolRegistry()
    tool = _Disburse()
    registry.register(tool)
    executor = ToolExecutor(registry, ExecutorConfig(timeout=5))
    gateway = GovernanceGateway(policy)
    executor.governance = gateway

    loop = AgentLoop(
        llm_client=object(),
        tool_executor=executor,
        context_builder=object(),
        session_manager=object(),
        config=None,
    )
    loop.governance_gateway = gateway
    loop.governance_context = gateway.new_context()
    loop.add_hook(_RewriteAmountHook())

    results = await loop._execute_tools(
        [ToolCall(id="1", name="loan:disburse", arguments={"amount": 100})],
        types.SimpleNamespace(id="sess-1"),
    )

    assert results[0].success is False
    assert "业务约束" in (results[0].error or "")
    assert tool.calls == [], "校验未通过的工具不得执行"


def test_strict_run_auto_assembles_gateway(tmp_path, monkeypatch):
    """strict 下 `run()` 自动装配网关（不依赖调用方显式调用）——fail-closed。"""
    from harness.skills import loader

    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "governed.md").write_text(SKILL_WITH_GOVERNANCE, encoding="utf-8")
    monkeypatch.setattr(loader, "DEFAULT_SKILL_PATHS", [skills])

    harness = AgentHarness(
        config=HarnessConfig(
            api_key="test-key",
            model="mock-model",
            strict=True,
            governance_agent_id="credit-paper-assembler",
        )
    )
    harness.register_tool(_Read())
    harness.register_tool(_Aml())
    assert harness._tool_executor.governance is None  # 构造期未装配

    import asyncio
    import contextlib

    async def _run():
        # LLM 是桩，run 本身可能失败；只验证装配副作用
        with contextlib.suppress(Exception):
            await harness.run("hi", session_id="s1")

    asyncio.run(_run())
    assert harness._tool_executor.governance is not None
    assert harness._loop.governance_gateway is not None
    # 客户端退出标记需要最近一次 run 的 id（§10.1/§10.4）
    assert harness.last_run_id == harness._loop.governance_context.run_id


def test_register_after_run_invalidates_policy(tmp_path, monkeypatch):
    """run 之后再注册工具 → 旧策略失效（避免用过期策略判定）。"""
    from harness.skills import loader

    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "governed.md").write_text(SKILL_WITH_GOVERNANCE, encoding="utf-8")
    monkeypatch.setattr(loader, "DEFAULT_SKILL_PATHS", [skills])

    harness = AgentHarness(
        config=HarnessConfig(
            api_key="test-key",
            model="mock-model",
            strict=True,
            governance_agent_id="credit-paper-assembler",
        )
    )
    harness.register_tool(_Read())
    harness.register_tool(_Aml())
    first = harness.governance_gateway()
    assert first is not None

    class _Extra(_Read):
        @property
        def name(self):
            return "extra:read"

    harness.register_tool(_Extra())
    assert harness._tool_executor.governance is None
    assert harness._governance_gateway is None


async def test_stream_path_creates_run_context_in_strict(tmp_path, monkeypatch):
    """流式 run 也创建 per-run 治理上下文并写 run 事件（§4.4）。"""
    from harness.llm.mock import MockLLMClient, MockResponse
    from harness.skills import loader

    skills = tmp_path / "skills"
    skills.mkdir()
    (skills / "governed.md").write_text(SKILL_WITH_GOVERNANCE, encoding="utf-8")
    monkeypatch.setattr(loader, "DEFAULT_SKILL_PATHS", [skills])

    harness = AgentHarness(
        config=HarnessConfig(
            api_key="test-key",
            model="mock-model",
            strict=True,
            governance_agent_id="credit-paper-assembler",
        ),
        llm_client=MockLLMClient(responses=[MockResponse(content="done")]),
    )
    harness.register_tool(_Read())
    harness.register_tool(_Aml())
    # 重定向事件目录，避免写 ~/.harness
    gateway = harness.governance_gateway()
    gateway.event_log.directory = tmp_path / "audit"

    chunks = []
    async for chunk in harness.stream("hi", session_id="s1"):
        chunks.append(chunk)

    assert harness._loop.governance_context is not None
    run_id = harness._loop.governance_context.run_id
    path = next((tmp_path / "audit").rglob("*.jsonl"))
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    kinds = [e["event"] for e in events]
    assert "run_start" in kinds
    assert "run_end" in kinds
    assert all(e["run_id"] == run_id for e in events if "run_id" in e)


# --------------------------------------------------------------------------
# 审批等待不阻塞事件循环 + 审批完成后再查控制面（§7.5.2 / §10.3）
# --------------------------------------------------------------------------

PAY_BLOCK = {
    "agent_id": "payment-agent",
    "version": "1.0.0",
    "approved_by": "PR #1",
    "business_intent": "放款",
    "owners": {"accountable": "x", "technical": "x"},
    "material": True,
    "tools": [
        {
            "name": "pay:transfer",
            "capability": "payment",
            "idempotent": False,
            "constraints": {"required_fields": ["amount"]},
        }
    ],
    "workflow": {"steps": [{"id": "disburse", "tools": ["pay:transfer"]}]},
    "limits": {
        "max_tool_calls_per_run": 5,
        "max_calls_per_minute": 5,
        "max_tokens_per_run": 1000,
    },
    "approval_required_for": ["pay:transfer"],
}


class _Pay(Tool):
    capability = "payment"
    idempotent = False

    def __init__(self) -> None:
        self.calls: list[dict] = []

    @property
    def name(self) -> str:
        return "pay:transfer"

    @property
    def description(self) -> str:
        return "pay"

    async def execute(self, arguments, context) -> ToolResult:
        self.calls.append(arguments)
        return ToolResult(tool_call_id="", success=True, content="paid")


def _payment_executor(tmp_path, timeout_seconds=1):
    from harness.governance.approval import ApprovalManager
    from harness.governance.control import ControlPlane

    policy = compile_policy(
        [parse_governance_block(yaml.safe_load(yaml.safe_dump(PAY_BLOCK)))]
    )
    registry = ToolRegistry()
    pay = _Pay()
    registry.register(pay)
    executor = ToolExecutor(registry, ExecutorConfig(timeout=5))
    control_dir = tmp_path / "control"
    plane = ControlPlane(directory=control_dir)
    manager = ApprovalManager(
        control_dir=control_dir, timeout_seconds=timeout_seconds, poll_interval=0.01
    )
    log = GovernanceEventLog(directory=tmp_path / "audit")
    gateway = GovernanceGateway(
        policy, approval=manager, control=plane, event_log=log
    )
    executor.governance = gateway
    return executor, gateway, manager, plane, pay


async def test_approval_wait_does_not_block_event_loop(tmp_path):
    """审批等待期间事件循环仍在跑（§7.5.2「不阻塞事件循环」）。"""
    import asyncio

    executor, gateway, _, _, pay = _payment_executor(tmp_path, timeout_seconds=1)
    ctx = gateway.new_context()

    ticks = 0

    async def ticker() -> None:
        nonlocal ticks
        while True:
            await asyncio.sleep(0.01)
            ticks += 1

    task = asyncio.create_task(ticker())
    try:
        result = await executor.execute(
            ToolCall(id="1", name="pay:transfer", arguments={"amount": 1}),
            _context(executor, ctx),
        )
    finally:
        task.cancel()

    assert result.success is False  # 无人审批 → 超时拒绝
    assert pay.calls == []
    assert ticks >= 10, f"事件循环被阻塞（ticks={ticks}）"


async def test_suspend_during_approval_blocks_execution(tmp_path):
    """审批完成后再查控制面：等待期间被 suspend，批准也不执行（§10.3）。"""
    import threading
    import time

    executor, gateway, manager, plane, pay = _payment_executor(
        tmp_path, timeout_seconds=5
    )
    ctx = gateway.new_context()

    def approve_then_suspend() -> None:
        deadline = time.time() + 5
        while time.time() < deadline:
            pending = manager.list_pending()
            if pending:
                plane.suspend("payment-agent", reason="during approval")
                manager.decide(pending[0].request_id, approved=True, actor="tester")
                return
            time.sleep(0.01)

    thread = threading.Thread(target=approve_then_suspend, daemon=True)
    thread.start()
    result = await executor.execute(
        ToolCall(id="1", name="pay:transfer", arguments={"amount": 1}),
        _context(executor, ctx),
    )
    thread.join(timeout=5)

    assert result.success is False
    assert "控制面" in (result.error or "")
    assert pay.calls == [], "审批通过但已被 suspend，不得执行工具"
