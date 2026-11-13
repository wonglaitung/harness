"""`governance draft`：LLM 只出草稿，确定性代码裁决。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from harness.types import LLMResponse
from harness_cli.draft import _make_client, governance_draft
from harness_cli.main import main

SKILL = """---
name: report-assembler
description: 汇总每日风险报告
tools:
  allowed: [read, glob, write]
---

先读取数据，再汇总，最后写报告。
"""

MCP_SKILL = """---
name: payment-agent
description: 处理付款
tools:
  allowed: [read, mcp_pay]
---

读取订单后付款。
"""

DRAFT = """\
business_intent: 汇总每日风险报告
material: false
tools:
  - name: read
    outputs:
      - name: raw
        from: metadata
        path: content
workflow:
  steps:
    - id: collect
      tools: [read, glob]
      complete: all
    - id: write_report
      tools: [write]
      requires: [collect]
limits:
  max_tool_calls_per_run: 20
"""


class FakeClient:
    """记录调用并返回固定响应。"""

    def __init__(self, content: str) -> None:
        self.content = content
        self.calls: list[dict[str, Any]] = []

    async def call(
        self,
        messages: list[dict[str, Any]],
        tools: Any = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        self.calls.append({"messages": messages, "system": system})
        return LLMResponse(content=self.content)


def _write(tmp_path: Path, content: str, name: str = "report.md") -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_draft_writes_full_block_and_keeps_human_fields(tmp_path, capsys):
    path = _write(tmp_path, SKILL)
    client = FakeClient(DRAFT)

    assert (
        governance_draft(
            str(path), agent_id="report-assembler", client=client, provider="openai"
        )
        == 0
    )

    text = path.read_text(encoding="utf-8")
    assert "agent_id: report-assembler" in text
    assert "business_intent: 汇总每日风险报告" in text
    assert "id: collect" in text
    assert "id: write_report" in text
    assert "max_tool_calls_per_run: 20" in text
    assert "# LLM 草稿" in text
    # 责任字段绝不由模型生成
    assert "approved_by: TODO" in text
    assert "accountable: TODO" in text
    assert len(client.calls) == 1
    assert "先读取数据" in client.calls[0]["messages"][0]["content"]
    captured = capsys.readouterr()
    assert "已写入 LLM 初稿（需人工确认）" in captured.out
    assert "仍需人工填写" in captured.err
    # 结构合法但仍有 TODO，check 必须拒绝
    assert main(["governance", "check", str(path)]) == 1


def test_draft_ignores_identity_and_accountability_fields(tmp_path, capsys):
    path = _write(tmp_path, SKILL)
    draft = DRAFT + "approved_by: evil\nowners:\n  accountable: evil\n"
    client = FakeClient(draft)

    assert (
        governance_draft(str(path), agent_id="real-agent", client=client) == 0
    )

    text = path.read_text(encoding="utf-8")
    assert "agent_id: real-agent" in text
    assert "approved_by: TODO" in text
    assert "accountable: TODO" in text
    assert "evil" not in text
    assert "已忽略模型输出的身份/责任字段" in capsys.readouterr().err


def test_draft_rejects_tool_outside_allowlist(tmp_path, capsys):
    path = _write(tmp_path, SKILL)
    before = path.read_text(encoding="utf-8")
    draft = DRAFT.replace("tools: [write]", "tools: [bash]")
    client = FakeClient(draft)

    assert governance_draft(str(path), agent_id="a", client=client) == 1

    assert "未声明的工具" in capsys.readouterr().err
    assert path.read_text(encoding="utf-8") == before


def test_draft_rejects_invalid_capability_for_unknown_tool(tmp_path, capsys):
    path = _write(tmp_path, MCP_SKILL, "pay.md")
    before = path.read_text(encoding="utf-8")
    draft = """\
business_intent: 付款
tools:
  - name: mcp_pay
    capability: admin
    idempotent: false
workflow:
  steps:
    - id: pay
      tools: [mcp_pay]
"""
    client = FakeClient(draft)

    assert governance_draft(str(path), agent_id="payment-agent", client=client) == 1

    assert "capability `admin` 非法" in capsys.readouterr().err
    assert path.read_text(encoding="utf-8") == before


def test_draft_accepts_capability_for_unknown_tool(tmp_path):
    path = _write(tmp_path, MCP_SKILL, "pay.md")
    draft = """\
business_intent: 付款
material: true
tools:
  - name: mcp_pay
    capability: payment
    idempotent: false
approval_required_for: [mcp_pay]
workflow:
  shared_tools: [read]
  steps:
    - id: pay
      tools: [mcp_pay]
"""
    client = FakeClient(draft)

    assert governance_draft(str(path), agent_id="payment-agent", client=client) == 0

    text = path.read_text(encoding="utf-8")
    assert "capability: payment" in text
    assert "approval_required_for:" in text


def test_draft_emit_prompt_does_not_need_client_or_write(tmp_path, capsys):
    path = _write(tmp_path, SKILL)
    before = path.read_text(encoding="utf-8")

    assert main(["governance", "draft", str(path), "--emit-prompt"]) == 0

    out = capsys.readouterr().out
    assert "[system]" in out
    assert "可用工具（只能使用这些）" in out
    assert "read" in out
    assert "steps.<step_id>.outputs.<name>" in out
    assert "GitHub Actions 的表达式语法" in out
    assert path.read_text(encoding="utf-8") == before


def test_draft_dry_run_does_not_write(tmp_path, capsys):
    path = _write(tmp_path, SKILL)
    before = path.read_text(encoding="utf-8")
    client = FakeClient(DRAFT)

    assert (
        governance_draft(str(path), agent_id="a", dry_run=True, client=client) == 0
    )

    out = capsys.readouterr().out
    assert "id: collect" in out
    assert path.read_text(encoding="utf-8") == before


def test_draft_skips_existing_governance(tmp_path, capsys):
    path = _write(
        tmp_path,
        SKILL.replace(
            "tools:\n  allowed: [read, glob, write]\n",
            "tools:\n  allowed: [read, glob, write]\n"
            "governance:\n  agent_id: x\n  version: 1.0.0\n"
            "  approved_by: x\n  business_intent: x\n"
            "  owners:\n    accountable: x\n    technical: x\n"
            "  material: false\n  tools:\n    - name: read\n"
            "      capability: read\n      idempotent: true\n"
            "  workflow:\n    steps:\n      - id: s1\n        tools: [read]\n"
            "  limits:\n    max_tool_calls_per_run: 10\n",
        ),
    )
    before = path.read_text(encoding="utf-8")
    client = FakeClient(DRAFT)

    assert governance_draft(str(path), client=client) == 0

    assert "跳过：已存在治理块" in capsys.readouterr().out
    assert client.calls == []
    assert path.read_text(encoding="utf-8") == before


def test_draft_requires_tools_allowed(tmp_path, capsys):
    path = _write(
        tmp_path,
        "---\nname: bare\ndescription: 没有工具\n---\n\n正文\n",
    )
    before = path.read_text(encoding="utf-8")
    client = FakeClient(DRAFT)

    assert governance_draft(str(path), client=client) == 1

    assert "未声明 tools.allowed" in capsys.readouterr().err
    assert path.read_text(encoding="utf-8") == before


def test_draft_rejects_non_mapping_response(tmp_path, capsys):
    path = _write(tmp_path, SKILL)
    before = path.read_text(encoding="utf-8")
    client = FakeClient("[]")

    assert governance_draft(str(path), agent_id="a", client=client) == 1

    assert "草稿未写入" in capsys.readouterr().err
    assert path.read_text(encoding="utf-8") == before


def test_draft_rejects_invalid_business_intent(tmp_path, capsys):
    path = _write(tmp_path, SKILL)
    before = path.read_text(encoding="utf-8")
    client = FakeClient(
        "business_intent: 1\nworkflow:\n  steps:\n    - id: s\n      tools: [read]\n"
    )

    assert governance_draft(str(path), agent_id="a", client=client) == 1

    assert "草稿未写入" in capsys.readouterr().err
    assert path.read_text(encoding="utf-8") == before


def test_make_client_passes_openai_compatible_base_url(monkeypatch):
    captured: dict[str, Any] = {}

    class SpyClient:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

    monkeypatch.setattr("harness.llm.OpenAIClient", SpyClient)

    _make_client(
        "openai", "my-model", 5.0, "https://gateway.example/v1", "sk-test"
    )

    assert captured["model"] == "my-model"
    assert captured["base_url"] == "https://gateway.example/v1"
    assert captured["api_key"] == "sk-test"
    assert captured["config"].timeout == 5.0


class SequenceClient(FakeClient):
    """按顺序返回多条响应（用于验证校验失败后的重试）。"""

    def __init__(self, contents: list[str]) -> None:
        super().__init__(contents[0])
        self.contents = contents

    async def call(
        self,
        messages: list[dict[str, Any]],
        tools: Any = None,
        system: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        self.calls.append({"messages": list(messages), "system": system})
        return LLMResponse(content=self.contents[min(len(self.calls) - 1, len(self.contents) - 1)])


def test_draft_retries_once_with_validation_feedback(tmp_path, capsys):
    path = _write(tmp_path, SKILL)
    bad = DRAFT.replace("tools: [write]", "tools: [bash]")
    client = SequenceClient([bad, DRAFT])

    assert governance_draft(str(path), agent_id="a", client=client) == 0

    assert len(client.calls) == 2
    repair = client.calls[1]["messages"]
    assert repair[-1]["role"] == "user"
    assert "未通过校验" in repair[-1]["content"]
    assert "草稿未写入" not in capsys.readouterr().err
    assert "id: collect" in path.read_text(encoding="utf-8")


def test_draft_retries_when_model_outputs_gha_job_structure(tmp_path):
    path = _write(tmp_path, SKILL)
    wrong = DRAFT + "jobs:\n  build:\n    runs-on: ubuntu-latest\n"
    client = SequenceClient([wrong, DRAFT])

    assert governance_draft(str(path), agent_id="a", client=client) == 0

    assert len(client.calls) == 2
    assert "jobs" in client.calls[1]["messages"][-1]["content"]
    assert "id: collect" in path.read_text(encoding="utf-8")
