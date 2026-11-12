"""治理块解析、校验、编译与运行上下文的单元测试。"""

from __future__ import annotations

import pytest
import yaml

from harness.governance import (
    GovernanceError,
    RunContext,
    compile_policy,
    validate_governance_block,
)
from harness.governance.expression import (
    ExpressionContext,
    ExpressionError,
    evaluate_expression,
    is_wrapped,
    parse_expression,
)
from harness.governance.schema import parse_governance_block

VALID_BLOCK = {
    "agent_id": "credit-paper-assembler",
    "version": "1.2.0",
    "approved_by": "PR #1284",
    "business_intent": "组装信贷报告初稿",
    "owners": {"accountable": "Head of Credit Risk", "technical": "DevOps Lead A"},
    "material": True,
    "tools": [
        {"name": "core_banking_api:read_only", "capability": "read", "idempotent": True},
        {"name": "aml_screening:run", "capability": "write", "idempotent": True,
         "outputs": [{"name": "aml_hit", "from": "metadata", "path": "aml_hit"}]},
        {"name": "report_writer:draft", "capability": "write", "idempotent": False},
        {"name": "review_submit:post", "capability": "write", "idempotent": True},
    ],
    "workflow": {
        "steps": [
            {"id": "collect_data", "tools": ["core_banking_api:read_only"]},
            {"id": "aml_check", "tools": ["aml_screening:run"]},
            {"id": "manual_review", "if": "${{ steps.aml_check.outputs.aml_hit == 'true' }}",
             "tools": ["review_submit:post"]},
            {"id": "draft_report", "tools": ["report_writer:draft"]},
        ]
    },
    "limits": {"max_tool_calls_per_run": 50, "max_calls_per_minute": 20,
               "max_tokens_per_run": 200000},
    "approval_required_for": ["draft_report"],
}


@pytest.fixture
def block():
    return parse_governance_block(yaml.safe_load(yaml.safe_dump(VALID_BLOCK)))


# --------------------------------------------------------------------------
# 解析
# --------------------------------------------------------------------------

def test_parse_valid_block(block):
    assert block.agent_id == "credit-paper-assembler"
    assert len(block.tools) == 4
    assert block.material is True
    assert [s.id for s in block.workflow.steps] == [
        "collect_data", "aml_check", "manual_review", "draft_report"
    ]
    assert block.workflow.steps[2].condition == (
        "${{ steps.aml_check.outputs.aml_hit == 'true' }}"
    )


def test_unknown_top_field_rejected():
    raw = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw["typo_field"] = 1
    with pytest.raises(GovernanceError, match="未知字段"):
        parse_governance_block(raw)


def test_unknown_tool_field_rejected():
    raw = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw["tools"][0]["capablity"] = "read"
    with pytest.raises(GovernanceError, match="未知字段"):
        parse_governance_block(raw)


def test_missing_required_field_rejected():
    raw = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    del raw["agent_id"]
    with pytest.raises(GovernanceError, match="agent_id"):
        parse_governance_block(raw)


def test_invalid_capability_rejected():
    raw = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw["tools"][0]["capability"] = "destroy"
    with pytest.raises(GovernanceError, match="capability"):
        parse_governance_block(raw)


def test_non_boolean_idempotent_rejected():
    raw = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw["tools"][0]["idempotent"] = "yes"
    with pytest.raises(GovernanceError, match="布尔"):
        parse_governance_block(raw)


# --------------------------------------------------------------------------
# 校验规则
# --------------------------------------------------------------------------

def _rules(result):
    return {e.rule for e in result.errors}


def test_valid_block_passes(block):
    result = validate_governance_block(block)
    assert result.ok, result.messages()


def test_rule6_unknown_field(block):
    raw = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw["tools"][0]["capability"] = "read"
    raw["tools"][0]["extra"] = 1
    with pytest.raises(GovernanceError):
        parse_governance_block(raw)


def test_rule3_duplicate_output_name_rejected():
    raw = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw["tools"][1]["outputs"].append({"name": "aml_hit", "from": "metadata", "path": "x"})
    block = parse_governance_block(raw)
    result = validate_governance_block(block)
    assert not result.ok
    assert 3 in _rules(result)


def test_rule13_if_references_unknown_output(block):
    raw = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw["workflow"]["steps"][2]["if"] = "${{ steps.aml_check.outputs.nope == 'true' }}"
    # 表达式本身合法；输出不存在由运行期判定，这里只校验解析
    block = parse_governance_block(raw)
    assert validate_governance_block(block).ok


def test_rule12_requires_must_precede(block):
    raw = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw["workflow"]["steps"][1]["requires"] = ["draft_report"]
    block = parse_governance_block(raw)
    result = validate_governance_block(block)
    assert not result.ok
    assert 12 in _rules(result)


def test_rule14_invalid_expression_rejected(block):
    raw = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw["workflow"]["steps"][2]["if"] = "${{ steps.aml_check.outputs.aml_hit == }}"
    block = parse_governance_block(raw)
    result = validate_governance_block(block)
    assert not result.ok
    assert 14 in _rules(result)


def test_rule15_forbidden_context_rejected(block):
    raw = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw["workflow"]["steps"][2]["if"] = "${{ secrets.FOO == 'x' }}"
    block = parse_governance_block(raw)
    result = validate_governance_block(block)
    assert not result.ok
    assert 15 in _rules(result)


def test_rule15_hashfiles_rejected(block):
    raw = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw["workflow"]["steps"][2]["if"] = "${{ hashFiles('**') != '' }}"
    block = parse_governance_block(raw)
    result = validate_governance_block(block)
    assert not result.ok
    assert 15 in _rules(result)


def test_rule17_unwrapped_expression_rejected(block):
    raw = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw["workflow"]["steps"][2]["if"] = "steps.aml_check.outputs.aml_hit == 'true'"
    block = parse_governance_block(raw)
    result = validate_governance_block(block)
    assert not result.ok
    assert 17 in _rules(result)


def test_rule18_bang_start_rejected(block):
    raw = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw["workflow"]["steps"][2]["if"] = "${{ !steps.aml_check.outputs.aml_hit == 'true' }}"
    block = parse_governance_block(raw)
    result = validate_governance_block(block)
    assert not result.ok
    assert 18 in _rules(result)


def test_rule20_payment_requires_approval(block):
    """payment 工具若不在被审批覆盖的 step 中 → 规则 20 触发。"""
    raw = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw["tools"].append({"name": "pay:transfer", "capability": "payment", "idempotent": False})
    # 放到 collect_data（未被 approval_required_for 覆盖）
    raw["workflow"]["steps"][0]["tools"].append("pay:transfer")
    block = parse_governance_block(raw)
    result = validate_governance_block(block)
    assert not result.ok
    assert 20 in _rules(result)


def test_rule20_payment_covered_is_ok(block):
    """payment 工具在被审批覆盖的 step 中 → 规则 20 不触发。"""
    raw = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw["tools"].append({"name": "pay:transfer", "capability": "payment", "idempotent": False})
    raw["workflow"]["steps"][3]["tools"].append("pay:transfer")  # draft_report 已声明审批
    block = parse_governance_block(raw)
    result = validate_governance_block(block)
    assert result.ok, result.messages()


def test_rule21_any_complete_rejects_destructive(block):
    raw = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw["tools"].append({"name": "db:drop", "capability": "destructive", "idempotent": False})
    raw["workflow"]["steps"][3]["tools"].append("db:drop")
    raw["workflow"]["steps"][3]["complete"] = "any"
    block = parse_governance_block(raw)
    result = validate_governance_block(block)
    assert not result.ok
    assert 21 in _rules(result)


def test_rule22_shared_tools_rejects_non_idempotent(block):
    raw = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw["workflow"]["shared_tools"] = ["report_writer:draft"]
    block = parse_governance_block(raw)
    result = validate_governance_block(block)
    assert not result.ok
    assert 22 in _rules(result)


def test_rule24_material_requires_workflow(block):
    raw = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw["workflow"] = {"steps": []}
    block = parse_governance_block(raw)
    result = validate_governance_block(block)
    assert not result.ok
    assert 24 in _rules(result)


def test_rule25_material_requires_forced_approval(block):
    raw = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw["tools"].append({"name": "pay:transfer", "capability": "payment", "idempotent": False})
    raw["workflow"]["steps"][3]["tools"].append("pay:transfer")
    raw["approval_required_for"] = []
    block = parse_governance_block(raw)
    result = validate_governance_block(block)
    assert not result.ok
    assert 25 in _rules(result)


def test_rule26_placeholder_rejected(block):
    raw = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw["approved_by"] = "TODO"
    block = parse_governance_block(raw)
    result = validate_governance_block(block)
    assert not result.ok
    assert 26 in _rules(result)


def test_rule27_step_tool_must_be_in_whitelist(block):
    raw = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw["workflow"]["steps"][0]["tools"].append("unknown:tool")
    block = parse_governance_block(raw)
    result = validate_governance_block(block)
    assert not result.ok
    assert 27 in _rules(result)


def test_rule28_whitelist_tool_needs_owner(block):
    raw = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw["tools"].append({"name": "orphan:tool", "capability": "read", "idempotent": True})
    block = parse_governance_block(raw)
    result = validate_governance_block(block)
    assert not result.ok
    assert 28 in _rules(result)


def test_rule29_governance_tools_subset_of_skill_allowed(block):
    result = validate_governance_block(
        block, skill_allowed_tools={"core_banking_api:read_only"}
    )
    assert not result.ok
    assert 29 in _rules(result)


def test_rule29_pass_when_subset(block):
    result = validate_governance_block(
        block, skill_allowed_tools={t.name for t in block.tools}
    )
    assert result.ok, result.messages()


# --------------------------------------------------------------------------
# 表达式
# --------------------------------------------------------------------------

def _ctx(**kwargs):
    steps = kwargs.pop("steps", {})
    return ExpressionContext(steps=steps, env=kwargs.pop("env", {}))


def test_expression_string_comparison():
    ctx = _ctx(steps={"a": {"outputs": {"hit": "true"}, "outcome": "success"}})
    assert evaluate_expression("${{ steps.a.outputs.hit == 'true' }}", ctx) is True
    assert evaluate_expression("${{ steps.a.outputs.hit == 'false' }}", ctx) is False


def test_expression_numeric_comparison():
    ctx = _ctx(steps={"a": {"outputs": {"score": "42"}, "outcome": "success"}})
    assert evaluate_expression("${{ steps.a.outputs.score > 30 }}", ctx) is True
    assert evaluate_expression("${{ steps.a.outputs.score > 50 }}", ctx) is False


def test_expression_logical_and():
    ctx = _ctx(steps={"a": {"outputs": {"x": "1", "y": "2"}, "outcome": "success"}})
    assert evaluate_expression("${{ steps.a.outputs.x == '1' && steps.a.outputs.y == '2' }}", ctx)
    assert not evaluate_expression(
        "${{ steps.a.outputs.x == '9' && steps.a.outputs.y == '2' }}", ctx
    )


def test_expression_outcome_reference():
    ctx = _ctx(steps={"a": {"outputs": {}, "outcome": "success"}})
    assert evaluate_expression("${{ steps.a.outcome == 'success' }}", ctx) is True


def test_expression_unknown_context_raises():
    ctx = _ctx()
    with pytest.raises(ExpressionError):
        evaluate_expression("${{ steps.nope.outputs.x == '1' }}", ctx)


def test_expression_forbidden_context_raises():
    with pytest.raises(ExpressionError, match="禁止"):
        parse_expression("${{ secrets.FOO == 'x' }}")


def test_expression_contains_function():
    ctx = _ctx(steps={"a": {"outputs": {"tags": "x,y"}, "outcome": "success"}})
    assert evaluate_expression("${{ contains(steps.a.outputs.tags, 'y') }}", ctx) is True


def test_is_wrapped():
    assert is_wrapped("${{ 1 == 1 }}")
    assert not is_wrapped("1 == 1")


# --------------------------------------------------------------------------
# PolicySnapshot 合成
# --------------------------------------------------------------------------

def test_compile_single_block(block):
    policy = compile_policy([block])
    assert policy.agent_id == "credit-paper-assembler"
    assert len(policy.tools) == 4
    assert policy.material is True


def test_compile_merges_whitelist_as_intersection():
    raw_a = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw_b = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw_b["tools"] = raw_b["tools"][:2]
    raw_b["workflow"]["steps"] = raw_b["workflow"]["steps"][:2]
    raw_b["workflow"]["steps"][1]["tools"] = ["aml_screening:run"]
    a = parse_governance_block(raw_a)
    b = parse_governance_block(raw_b)
    policy = compile_policy([a, b])
    assert policy.tool_names == {"core_banking_api:read_only", "aml_screening:run"}


def test_compile_capability_conflict_rejected():
    raw_a = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw_b = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw_b["tools"][0]["capability"] = "write"
    a = parse_governance_block(raw_a)
    b = parse_governance_block(raw_b)
    with pytest.raises(GovernanceError, match="capability 冲突"):
        compile_policy([a, b])


def test_compile_limits_take_strictest():
    raw_a = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw_b = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw_b["limits"]["max_tool_calls_per_run"] = 10
    policy = compile_policy([parse_governance_block(raw_a), parse_governance_block(raw_b)])
    assert policy.limits.max_tool_calls_per_run == 10


def test_requires_approval_semantics(block):
    policy = compile_policy([block])
    assert policy.requires_approval("report_writer:draft") is True   # write + 显式声明
    assert policy.requires_approval("core_banking_api:read_only") is False
    assert policy.requires_approval("aml_screening:run") is False


def test_payment_always_requires_approval(block):
    raw = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw["tools"].append({"name": "pay:transfer", "capability": "payment", "idempotent": False})
    policy = compile_policy([parse_governance_block(raw)])
    assert policy.requires_approval("pay:transfer") is True


# --------------------------------------------------------------------------
# 运行上下文 / 游标
# --------------------------------------------------------------------------

def test_run_context_generates_run_id(block):
    ctx = RunContext(compile_policy([block]))
    assert len(ctx.run_id) == 32


def test_cursor_advances_after_success(block):
    ctx = RunContext(compile_policy([block]))
    step = ctx.current_step()
    assert step.id == "collect_data"
    ctx.record_tool_success("collect_data", "core_banking_api:read_only", {})
    assert ctx.advance_cursor().id == "aml_check"


def test_cursor_skips_inactive_branch(block):
    """AML 未命中 → manual_review 被 skipped → 继续推进到 draft_report。"""
    ctx = RunContext(compile_policy([block]))
    ctx.record_tool_success("collect_data", "core_banking_api:read_only", {})
    ctx.advance_cursor()
    ctx.record_tool_success("aml_check", "aml_screening:run", {"aml_hit": "false"})
    assert ctx.advance_cursor().id == "draft_report"
    assert ctx.step_state("manual_review").outcome == "skipped"


def test_cursor_takes_branch_when_hit(block):
    ctx = RunContext(compile_policy([block]))
    ctx.record_tool_success("collect_data", "core_banking_api:read_only", {})
    ctx.advance_cursor()
    ctx.record_tool_success("aml_check", "aml_screening:run", {"aml_hit": "true"})
    assert ctx.advance_cursor().id == "manual_review"


def test_failure_blocks_downstream(block):
    ctx = RunContext(compile_policy([block]))
    ctx.record_tool_success("collect_data", "core_banking_api:read_only", {})
    ctx.advance_cursor()
    ctx.record_tool_failure("aml_check", "aml_screening:run")
    assert ctx.step_state("aml_check").outcome == "failure"
    reachable, reason = ctx.is_reachable("report_writer:draft")
    assert not reachable
    assert "失败" in reason


def test_skip_does_not_block_downstream(block):
    ctx = RunContext(compile_policy([block]))
    ctx.record_tool_success("collect_data", "core_banking_api:read_only", {})
    ctx.advance_cursor()
    ctx.record_tool_success("aml_check", "aml_screening:run", {"aml_hit": "false"})
    ctx.advance_cursor()
    reachable, _ = ctx.is_reachable("report_writer:draft")
    assert reachable


def test_jump_step_is_denied(block):
    ctx = RunContext(compile_policy([block]))
    reachable, reason = ctx.is_reachable("report_writer:draft")
    assert not reachable
    assert "跳步" in reason


def test_guard_unresolved_is_fail_closed(block):
    """条件求值失败 → 视为 if 为假（分支不激活）+ 记 guard_unresolved。"""
    raw = yaml.safe_load(yaml.safe_dump(VALID_BLOCK))
    raw["workflow"]["steps"][2]["if"] = "${{ steps.aml_check.outputs.aml_hit == 'true' }}"
    ctx = RunContext(compile_policy([parse_governance_block(raw)]))
    ctx.record_tool_success("collect_data", "core_banking_api:read_only", {})
    ctx.advance_cursor()
    ctx.record_tool_success("aml_check", "aml_screening:run", {})  # 未产出 aml_hit
    assert ctx.advance_cursor().id == "draft_report"
    assert ctx.signal_count("guard_unresolved") == 1
    assert ctx.step_state("manual_review").outcome == "skipped"


def test_rate_limit(block):
    ctx = RunContext(compile_policy([block]))
    for _ in range(20):
        ctx.note_call(1000.0)
    assert ctx.check_rate_limit(1000.0) is True


def test_run_limit(block):
    ctx = RunContext(compile_policy([block]))
    for _ in range(50):
        ctx.note_call(1000.0)
    assert ctx.check_run_limit() is False
    ctx.note_call(1000.0)
    assert ctx.check_run_limit() is True


def test_expression_equality_is_strict():
    """`==` 是严格相等：字符串产出不做数字转换（GHA 语义）。"""
    ctx = _ctx(steps={"a": {"outputs": {"v": "1"}, "outcome": "success"}})
    assert evaluate_expression("${{ steps.a.outputs.v == '1' }}", ctx) is True
    assert evaluate_expression("${{ steps.a.outputs.v == 1 }}", ctx) is False


def test_expression_order_comparison_converts():
    """顺序比较才做数字转换（产出全为字符串）。"""
    ctx = _ctx(steps={"a": {"outputs": {"v": "42"}, "outcome": "success"}})
    assert evaluate_expression("${{ steps.a.outputs.v > 30 }}", ctx) is True
