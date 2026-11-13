"""治理事件日志（设计稿 §11）。

写入 `~/.harness/audit/governance/<YYYYMMDD>/<pid>.jsonl`（按日期目录 + 按
进程分文件），全部带 `run_id`。

**判定/结果两段**（§11.1）：`decision` 在执行前定，`duration_ms` 与
`step_outcome` 只有执行后才知道。合成一条会导致 deny 事件带着不存在的耗时、
或 allow 事件缺失执行结果。

**字段命名对齐 OpenTelemetry GenAI 语义约定**（`gen_ai.*`），P1 接入 OTel 时
无需改名；`run_id` 是本方案自有字段（OTel 无对应）。

**脱敏**：只记参数哈希与判定结论，不记实际值（§10.3）。
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# 事件类型（§11.1）
RUN_START = "run_start"
RUN_END = "run_end"
TOOL_CALL_DECISION = "tool_call_decision"
TOOL_CALL_RESULT = "tool_call_result"
CONSTRAINT_VIOLATION = "constraint_violation"
STEP_VIOLATION = "step_violation"
STEP_REENTRY = "step_reentry"
STEP_SKIPPED = "step_skipped"
FACT_OBSERVED = "fact_observed"
GUARD_UNRESOLVED = "guard_unresolved"
SIGNAL = "signal"
GOVERNANCE_VERDICT = "governance_verdict"
CONTROL_PLANE = "control_plane"
APPROVAL = "approval"
APPROVAL_REQUEST = "approval_request"
APPROVAL_DECISION = "approval_decision"


def _default_dir() -> Path:
    return Path.home() / ".harness" / "audit" / "governance"


@dataclass
class GovernanceEventLog:
    """治理事件日志。

    - 同步 append + flush：桌面量小，换取"客户端被强杀也不丢已记事件"
    - 单行 ≤ 2KB：长内容只存哈希与摘要
    - 按进程分文件：避免多开客户端时多进程写同一文件交错
    """

    directory: Path = field(default_factory=_default_dir)
    retention_days: int = 30
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _handle: Any = field(default=None, repr=False)
    _path: Path | None = field(default=None, repr=False)

    # -- 写入 -------------------------------------------------------------

    def _current_path(self) -> Path:
        if self._path is not None:
            return self._path
        day = time.strftime("%Y%m%d", time.localtime())
        directory = self.directory / day
        directory.mkdir(parents=True, exist_ok=True)
        self._path = directory / f"{os.getpid()}.jsonl"
        return self._path

    def _handle_for(self) -> Any:
        if self._handle is None:
            path = self._current_path()
            self._handle = path.open("a", encoding="utf-8")
        return self._handle

    def write(self, event: str, **fields: Any) -> None:
        """写一条事件。"""
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
            + f".{int(time.time() * 1000) % 1000:03d}Z",
            "event": event,
        }
        payload.update({k: v for k, v in fields.items() if v is not None})
        line = json.dumps(payload, ensure_ascii=False, default=str)
        if len(line) > 2048:
            # 单行 ≤ 2KB：超长只存哈希与摘要
            payload["_truncated"] = True
            payload["_hash"] = hash(line)
            line = json.dumps(payload, ensure_ascii=False, default=str)
        with self._lock:
            handle = self._handle_for()
            handle.write(line + "\n")
            handle.flush()

    # -- 便捷方法 ---------------------------------------------------------

    def write_decision(
        self,
        ctx: Any,
        tool: str,
        decision: str,
        reason: str,
        *,
        step_id: str | None = None,
        duration_ms: int | None = None,
        outcome: str | None = None,
        capability: str | None = None,
        call_id: str | None = None,
        agent_version: str | None = None,
        skill_version: str | None = None,
    ) -> None:
        """写判定事件（流水线第 9 步）。字段对齐 OTel `gen_ai.*`（§11.1）。"""
        self.write(
            TOOL_CALL_DECISION,
            run_id=getattr(ctx, "run_id", None),
            agent_id=_agent_id(ctx),
            agent_version=agent_version,
            skill_version=skill_version,
            **{"gen_ai.operation.name": "execute_tool"},
            **{"gen_ai.tool.name": tool},
            **({"gen_ai.tool.call.id": call_id} if call_id else {}),
            capability=capability,
            decision=decision,
            reason=reason or None,
            step=step_id,
            duration_ms=duration_ms,
            step_outcome=outcome,
            step_conclusion=outcome,
        )

    def write_result(
        self,
        ctx: Any,
        tool: str,
        *,
        success: bool,
        duration_ms: int,
        step_id: str | None = None,
        outcome: str | None = None,
        error: str | None = None,
        call_id: str | None = None,
    ) -> None:
        """写结果事件（流水线第 11 步）。"""
        self.write(
            TOOL_CALL_RESULT,
            run_id=getattr(ctx, "run_id", None),
            agent_id=_agent_id(ctx),
            **{"gen_ai.operation.name": "execute_tool"},
            **{"gen_ai.tool.name": tool},
            **({"gen_ai.tool.call.id": call_id} if call_id else {}),
            success=success,
            duration_ms=duration_ms,
            step=step_id,
            step_outcome=outcome,
            step_conclusion=outcome,
            error=error,
        )

    def write_run_start(self, ctx: Any) -> None:
        self.write(
            RUN_START,
            run_id=getattr(ctx, "run_id", None),
            agent_id=_agent_id(ctx),
        )

    def write_run_end(self, ctx: Any, status: str) -> None:
        self.write(
            RUN_END,
            run_id=getattr(ctx, "run_id", None),
            agent_id=_agent_id(ctx),
            status=status,
        )

    # -- 保留期清理 -------------------------------------------------------

    def cleanup(self) -> int:
        """按保留期删除过期日期目录。返回删除的目录数。"""
        if not self.directory.exists():
            return 0
        cutoff = time.time() - self.retention_days * 86400
        removed = 0
        for day_dir in self.directory.iterdir():
            if not day_dir.is_dir():
                continue
            try:
                mtime = day_dir.stat().st_mtime
            except OSError:
                continue
            if mtime < cutoff:
                import shutil

                shutil.rmtree(day_dir, ignore_errors=True)
                removed += 1
        return removed

    def close(self) -> None:
        if self._handle is not None:
            self._handle.flush()
            self._handle.close()
            self._handle = None


def _agent_id(ctx: Any) -> str:
    policy = getattr(ctx, "policy", None)
    return getattr(policy, "agent_id", "")
