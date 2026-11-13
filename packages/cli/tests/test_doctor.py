"""CLI 入口与 doctor 的冒烟测试。"""

from __future__ import annotations


def test_cli_help_returns_zero() -> None:
    from harness_cli.main import main

    assert main([]) == 0


def test_cli_doctor_no_auditor_returns_one(monkeypatch) -> None:
    from harness_cli import doctor

    monkeypatch.setattr(doctor.shutil, "which", lambda _x: None)
    assert doctor.doctor_deps() == 1
