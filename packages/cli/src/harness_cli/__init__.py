"""Harness 的创作期/运维期命令行工具。

与运行时包 ``harness-sdk`` 分开：本包依赖 SDK，SDK 不依赖本包。治理的
强制力在 SDK 运行时（``AgentHarness`` + ``GovernanceGateway``），这里只
提供治理块生成/校验、审批、Kill Switch 与依赖诊断等确定性命令。
"""

from __future__ import annotations

from harness_cli.main import main

__all__ = ["main"]
