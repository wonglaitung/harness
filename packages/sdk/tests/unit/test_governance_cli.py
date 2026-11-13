"""治理 CLI 的测试（设计稿 §13.4 / §7.5.3 / §10.2）。

覆盖：
- `init` 只产出带 TODO 的骨架、**不写文件**、拒绝覆盖已有治理块
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


def test_init_prints_skeleton_with_todo_and_does_not_write(tmp_path, capsys):
    path = _write(tmp_path, "plain.md", PLAIN_SKILL)
    before = path.read_text(encoding="utf-8")

    assert main(["governance", "init", str(path)]) == 0

    out = capsys.readouterr()
    assert "capability: TODO" in out.out
    assert "idempotent: TODO" in out.out
    assert "agent_id: plain" in out.out
    assert "①" in out.err  # 九步清单
    assert path.read_text(encoding="utf-8") == before, "init 不得写文件"


def test_init_refuses_to_overwrite_existing_governance(tmp_path):
    path = _write(tmp_path, "good.md", GOOD_SKILL)
    assert main(["governance", "init", str(path)]) == 1


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
