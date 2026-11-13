"""Kill Switch 控制面（设计稿 §10）。

状态文件：`~/.harness/control/<agent_id>.json`，三态
``active`` / ``suspended`` / ``revoked``。

设计要点：
- **文件不存在即视为 `active`**（不写即不禁）
- **读取失败或内容损坏 → fail-closed**：按 `suspended` 处理。熔断开关被截断
  等于解除熔断，是控制面的静默失效——宁可过度阻断，不可静默放行（§10.1）
- **原子写**：临时文件 + `os.replace`，单机多写者（CLI + 客户端 UI）不会
  读到半个文件
- **agent 级与 run 级分离**：agent 级状态在本文件；run 级收尾状态在
  ``runs/<run_id>.json``（客户端退出写 run 级，不污染 agent 级）
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# agent 级状态
ACTIVE = "active"
SUSPENDED = "suspended"
REVOKED = "revoked"
STATES = (ACTIVE, SUSPENDED, REVOKED)

# run 级收尾状态
RUN_FINISHED = "finished"
RUN_CLIENT_SHUTDOWN = "client_shutdown"
RUN_INTERRUPTED = "interrupted"


def _default_dir() -> Path:
    return Path.home() / ".harness" / "control"


def _parse_timestamp(value: Any) -> float:
    """时间戳解析：兼容 epoch 浮点与 ISO 字符串（§10.1 的 JSON 样例用 ISO）。"""
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        try:
            return float(text)
        except ValueError:
            pass
        try:
            from datetime import datetime

            return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
        except ValueError:
            return 0.0
    return 0.0


def _parse_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


@dataclass
class ControlState:
    """一个 Agent 的控制状态。"""

    agent_id: str
    state: str = ACTIVE
    reason: str = ""
    actor: str = ""
    updated_at: float = 0.0
    version: int = 0

    @property
    def blocking(self) -> bool:
        """该状态是否阻断执行。"""
        return self.state in (SUSPENDED, REVOKED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "state": self.state,
            "reason": self.reason,
            "actor": self.actor,
            "updated_at": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.updated_at)
            ),
            "version": self.version,
        }


@dataclass
class ControlPlane:
    """控制面读写。"""

    directory: Path = field(default_factory=_default_dir)

    # -- 路径 -------------------------------------------------------------

    def _agent_path(self, agent_id: str) -> Path:
        return self.directory / f"{agent_id}.json"

    def _run_path(self, run_id: str) -> Path:
        return self.directory / "runs" / f"{run_id}.json"

    # -- 读 ---------------------------------------------------------------

    def read(self, agent_id: str) -> ControlState:
        """读 agent 级状态。

        - 文件不存在 → `active`（不写即不禁）
        - 读取失败 / 内容损坏 → `suspended`（fail-closed）
        """
        path = self._agent_path(agent_id)
        if not path.exists():
            return ControlState(agent_id=agent_id, state=ACTIVE)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return ControlState(
                agent_id=agent_id,
                state=SUSPENDED,
                reason="控制文件损坏或不可读，按 suspended 处理（fail-closed）",
            )
        state = data.get("state", ACTIVE)
        if state not in STATES:
            return ControlState(
                agent_id=agent_id,
                state=SUSPENDED,
                reason=f"控制文件状态非法（{state!r}），按 suspended 处理",
            )
        return ControlState(
            agent_id=agent_id,
            state=state,
            reason=data.get("reason", ""),
            actor=data.get("actor", ""),
            updated_at=_parse_timestamp(data.get("updated_at")),
            version=_parse_int(data.get("version")),
        )

    def read_run(self, run_id: str) -> dict[str, Any] | None:
        """读 run 级收尾状态。"""
        path = self._run_path(run_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None

    # -- 写 ---------------------------------------------------------------

    def _write_atomic(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(tmp, path)

    def write(self, state: ControlState) -> None:
        """写 agent 级状态（原子替换）。"""
        self._write_atomic(self._agent_path(state.agent_id), state.to_dict())

    def set_state(
        self,
        agent_id: str,
        state: str,
        *,
        reason: str = "",
        actor: str = "",
    ) -> ControlState:
        """设置 agent 级状态。重复设置同态幂等（version 递增）。"""
        if state not in STATES:
            raise ValueError(f"未知状态 {state!r}，只允许 {list(STATES)}")
        current = self.read(agent_id)
        new = ControlState(
            agent_id=agent_id,
            state=state,
            reason=reason,
            actor=actor,
            updated_at=time.time(),
            version=current.version + 1,
        )
        self.write(new)
        return new

    def suspend(
        self, agent_id: str, *, reason: str = "", actor: str = ""
    ) -> ControlState:
        return self.set_state(agent_id, SUSPENDED, reason=reason, actor=actor)

    def resume(
        self, agent_id: str, *, reason: str = "", actor: str = ""
    ) -> ControlState:
        return self.set_state(agent_id, ACTIVE, reason=reason, actor=actor)

    def revoke(
        self, agent_id: str, *, reason: str = "", actor: str = ""
    ) -> ControlState:
        return self.set_state(agent_id, REVOKED, reason=reason, actor=actor)

    def mark_run(
        self, run_id: str, status: str, *, agent_id: str = ""
    ) -> None:
        """写 run 级收尾状态（不污染 agent 级）。"""
        self._write_atomic(
            self._run_path(run_id),
            {
                "run_id": run_id,
                "agent_id": agent_id,
                "status": status,
                "updated_at": time.time(),
            },
        )
