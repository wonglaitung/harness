"""治理 CLI 的测试（设计稿 §13.4 / §7.5.3 / §10.2）。

覆盖：
- `init` 默认写入治理块：内置工具声明自动回填，只能人填的保留 TODO 并标
  「需手工补充」；`--dry-run` 不写；拒绝覆盖已有治理块
- `check` 逐条报 `file:line` + 规则号、非零退出
- `approve` / `reject` 复用 `ApprovalManager.decide`
- `suspend` / `resume` / `status` 复用 `ControlPlane`
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness.cli import main

GOOD_SKILL = """---
name: good-skill
description: 合法治理块
tools:
  allowed: [t1]
governance:
  agent_id: good-skill
  version: 1.0.0
  approved_by: "PR #1"
  business_intent: x
  owners:
    accountable: x
    technical: x
  material: false
  tools:
    - name: t1
      capability: read
      idempotent: true
  workflow:
    steps:
      - id: s1
        tools: [t1]
  limits:
    max_tool_calls_per_run: 10
---

正文
"""

BAD_SKILL = """---
name: bad-skill
description: 坏治理块
tools:
  allowed: [t1, t2]
governance:
  agent_id: bad-skill
  version: 1.0.0
  approved_by: "PR #1"
  business_intent: x
  owners:
    accountable: x
    technical: x
  material: true
  tools:
    - name: t1
      capability: read
      idempotent: true
    - name: t2
      capability: write
      idempotent: true
  workflow:
    steps:
      - id: s1
        tools: [t1]
      - id: s2
        tools: [t2]
        if: "${{ secrets.X == 'a' }}"
  limits:
    max_tool_calls_per_run: 10
---

正文
"""

PLAIN_SKILL = """---
name: plain
description: 没有治理块
tools:
  allowed: [t1]
---

正文
"""

BUILTIN_SKILL = """---
name: builtin-skill
description: 使用内置工具
tools:
  allowed: [read, glob]
---

正文
"""

MCP_SKILL = """---
name: mcp-skill
description: 混合内置与 MCP 工具
tools:
  allowed: [read, mcp_pay]
---

正文
"""


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def _write(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# init
# --------------------------------------------------------------------------


def test_init_writes_block_and_prefills_builtin_declarations(tmp_path, capsys):
    path = _write(tmp_path, "builtin.md", BUILTIN_SKILL)

    assert main(["governance", "init", str(path)]) == 0

    text = path.read_text(encoding="utf-8")
    assert "governance:" in text
    assert "capability: read" in text
    assert "idempotent: true" in text
    assert "tools: [read, glob]" in text
    # 只能人填的字段保留 TODO
    assert "approved_by: TODO" in text
    assert "business_intent: TODO" in text

    out, err = capsys.readouterr()
    assert "已写入治理块" in out
    assert "需手工补充" in err
    assert "business_intent" in err
    assert "agent_id（当前取技能名 `builtin-skill`" in err


def test_init_marks_unknown_tools_as_manual(tmp_path, capsys):
    path = _write(tmp_path, "mcp.md", MCP_SKILL)

    assert main(["governance", "init", str(path)]) == 0

    text = path.read_text(encoding="utf-8")
    assert "capability: read" in text
    assert "name: mcp_pay\n      capability: TODO\n      idempotent: TODO" in text
    assert "tools[mcp_pay].capability/idempotent" in capsys.readouterr().err


def test_init_written_block_fails_check_until_todo_is_filled(tmp_path, capsys):
    path = _write(tmp_path, "plain.md", PLAIN_SKILL)
    assert main(["governance", "init", str(path)]) == 0
    capsys.readouterr()

    assert main(["governance", "check", str(path)]) == 1
    assert "TODO" in capsys.readouterr().err


def test_init_dry_run_does_not_write(tmp_path, capsys):
    path = _write(tmp_path, "plain.md", PLAIN_SKILL)
    before = path.read_text(encoding="utf-8")

    assert main(["governance", "init", str(path), "--dry-run"]) == 0

    out, err = capsys.readouterr()
    assert "governance:" in out
    assert "需手工补充" in err
    assert path.read_text(encoding="utf-8") == before, "--dry-run 不得写文件"


def test_init_refuses_to_overwrite_existing_governance(tmp_path, capsys):
    path = _write(tmp_path, "good.md", GOOD_SKILL)
    before = path.read_text(encoding="utf-8")

    assert main(["governance", "init", str(path)]) == 0

    assert "跳过：已存在治理块" in capsys.readouterr().out
    assert path.read_text(encoding="utf-8") == before


def test_init_accepts_agent_id_flag(tmp_path):
    path = _write(tmp_path, "plain.md", PLAIN_SKILL)
    assert main(["governance", "init", str(path), "--agent-id", "report-assembler"]) == 0
    assert "agent_id: report-assembler" in path.read_text(encoding="utf-8")


def test_init_accepts_agent_id_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("HARNESS_GOVERNANCE_AGENT_ID", "env-agent")
    path = _write(tmp_path, "plain.md", PLAIN_SKILL)
    assert main(["governance", "init", str(path)]) == 0
    assert "agent_id: env-agent" in path.read_text(encoding="utf-8")


def test_init_directory_scans_skills_and_ignores_other_markdown(tmp_path, capsys):
    skills = tmp_path / "skills"
    skills.mkdir()
    _write(skills, "one.md", BUILTIN_SKILL)
    _write(skills, "two.md", PLAIN_SKILL)
    (skills / "README.md").write_text("# 不是技能\n", encoding="utf-8")

    assert main(["governance", "init", str(skills)]) == 0

    assert "governance:" in (skills / "one.md").read_text(encoding="utf-8")
    assert "governance:" in (skills / "two.md").read_text(encoding="utf-8")
    assert (skills / "README.md").read_text(encoding="utf-8") == "# 不是技能\n"


def test_init_missing_file_returns_error(tmp_path):
    assert main(["governance", "init", str(tmp_path / "nope.md")]) == 1


# --------------------------------------------------------------------------
# check
# --------------------------------------------------------------------------


def test_check_passes_for_valid_block(tmp_path, capsys):
    path = _write(tmp_path, "good.md", GOOD_SKILL)
    assert main(["governance", "check", str(path)]) == 0
    assert "校验通过" in capsys.readouterr().out


def test_check_reports_rule_and_line(tmp_path, capsys):
    path = _write(tmp_path, "bad.md", BAD_SKILL)
    assert main(["governance", "check", str(path)]) == 1
    err = capsys.readouterr().err
    assert "规则 15" in err
    assert f"{path}:" in err
    # 定位到 `if:` 所在行（不是第 1 行）
    assert f"{path}:1:" not in err


def test_check_missing_governance(tmp_path, capsys):
    path = _write(tmp_path, "plain.md", PLAIN_SKILL)
    assert main(["governance", "check", str(path)]) == 1
    assert "治理块缺失" in capsys.readouterr().err


def test_check_parse_error(tmp_path, capsys):
    broken = PLAIN_SKILL.replace(
        "  allowed: [t1]",
        "  allowed: [t1]\ngovernance:\n  agent_id: x",
    )
    path = _write(tmp_path, "broken.md", broken)
    assert main(["governance", "check", str(path)]) == 1
    assert "解析失败" in capsys.readouterr().err


# --------------------------------------------------------------------------
# approve / reject
# --------------------------------------------------------------------------


def test_approve_marks_request_approved(home):
    from harness.governance.approval import ApprovalManager

    manager = ApprovalManager()
    request = manager.create_request(
        run_id="run-1",
        agent_id="a",
        tool="pay:transfer",
        arguments={"amount": 1},
        capability="payment",
        reason="test",
    )
    assert main(["governance", "approve", request.request_id, "--actor", "alice"]) == 0

    data = json.loads(request.path.read_text(encoding="utf-8"))
    assert data["status"] == "approved"
    assert data["decided_by"] == "alice"


def test_reject_marks_request_rejected(home):
    from harness.governance.approval import ApprovalManager

    manager = ApprovalManager()
    request = manager.create_request(
        run_id="run-1",
        agent_id="a",
        tool="pay:transfer",
        arguments={"amount": 1},
        capability="payment",
        reason="test",
    )
    assert (
        main(
            ["governance", "reject", request.request_id, "--actor", "bob", "--reason", "no"]
        )
        == 0
    )
    data = json.loads(request.path.read_text(encoding="utf-8"))
    assert data["status"] == "rejected"


def test_approve_unknown_request_returns_error(home):
    assert main(["governance", "approve", "apr-9999"]) == 1


# --------------------------------------------------------------------------
# suspend / resume / status
# --------------------------------------------------------------------------


def test_suspend_resume_status(home, capsys):
    assert main(["governance", "suspend", "agent-a", "--reason", "AML 被跳过"]) == 0
    state = json.loads(capsys.readouterr().out)
    assert state["state"] == "suspended"

    assert main(["governance", "status", "agent-a"]) == 0
    state = json.loads(capsys.readouterr().out)
    assert state["state"] == "suspended"
    assert state["reason"] == "AML 被跳过"

    assert main(["governance", "resume", "agent-a", "--reason", "已复核"]) == 0
    state = json.loads(capsys.readouterr().out)
    assert state["state"] == "active"


def test_status_defaults_to_active(home, capsys):
    assert main(["governance", "status", "never-seen"]) == 0
    state = json.loads(capsys.readouterr().out)
    assert state["state"] == "active"
