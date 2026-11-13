"""运行期人工审批（设计稿 §7.5）。

`payment` / `destructive` 工具**恒需**人工审批（治理块不可关闭，§6.3）；
`write` 需治理块显式声明才需审批（§6.3）。

机制要点（§7.5）：
- **参数哈希绑定**：审批只对 `args_hash` 对应的这组参数有效。工具执行前重算
  哈希，不一致 → 审批失效，重新申请。防止"批准小额、改成大额"。
- **先落盘再等待**：请求写入 `~/.harness/control/approvals/<run_id>/<seq>.json`，
  写失败 → 拒绝（fail-closed，不放行未落盘的审批请求）。
- **等待语义**：阻塞该次工具调用，不阻塞事件循环；超时默认 5 分钟 → 拒绝。
- **无通道则 fail-closed**：审批通道不可用时不得放行高风险调用。

审批人身份是自由文本（桌面单机下无认证）——这是协作约定，**不是安全边界**
（§7.5.4）。真正的信任边界是"谁能写 `~/.harness/control/`"。
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _harness_control_dir() -> Path:
    return Path.home() / ".harness" / "control"


def args_hash(arguments: dict[str, Any]) -> str:
    """参数哈希（审批绑定用）。

    键排序后序列化，保证同一组参数在任何调用顺序下得到同一哈希。
    """
    payload = json.dumps(arguments, sort_keys=True, ensure_ascii=False, default=str)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class ApprovalRequest:
    """一个待审批请求。"""

    request_id: str
    run_id: str
    agent_id: str
    tool: str
    args_hash: str
    capability: str
    reason: str
    requested_at: float
    expires_at: float
    status: str = "pending"
    step: str | None = None
    path: Path | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "step": self.step,
            "tool": self.tool,
            "args_hash": self.args_hash,
            "capability": self.capability,
            "reason": self.reason,
            "requested_at": self.requested_at,
            "expires_at": self.expires_at,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], path: Path | None = None) -> ApprovalRequest:
        return cls(
            request_id=data.get("request_id", ""),
            run_id=data.get("run_id", ""),
            agent_id=data.get("agent_id", ""),
            tool=data.get("tool", ""),
            args_hash=data.get("args_hash", ""),
            capability=data.get("capability", ""),
            reason=data.get("reason", ""),
            requested_at=float(data.get("requested_at", 0.0)),
            expires_at=float(data.get("expires_at", 0.0)),
            status=data.get("status", "pending"),
            step=data.get("step"),
            path=path,
        )


@dataclass
class ApprovalManager:
    """审批管理器：落盘请求、等待决定。

    `decide` 由 CLI / 客户端 UI 调用（复用同一落点，见 §7.5.3）。
    """

    control_dir: Path = field(default_factory=_harness_control_dir)
    timeout_seconds: int = 300
    poll_interval: float = 0.25
    # 便于测试：注入时钟与等待函数
    _clock: Any = field(default=time.monotonic, repr=False)
    _sleep: Any = field(default=time.sleep, repr=False)

    # -- 请求 -------------------------------------------------------------

    def _request_dir(self, run_id: str) -> Path:
        return self.control_dir / "approvals" / run_id

    def create_request(
        self,
        *,
        run_id: str,
        agent_id: str,
        tool: str,
        arguments: dict[str, Any],
        capability: str,
        reason: str,
        timeout_seconds: int | None = None,
        step: str | None = None,
    ) -> ApprovalRequest:
        """创建并**落盘**审批请求。落盘失败抛异常（调用方 fail-closed）。"""
        timeout = self.timeout_seconds if timeout_seconds is None else timeout_seconds
        now = time.time()
        request_dir = self._request_dir(run_id)
        request_dir.mkdir(parents=True, exist_ok=True)
        seq = len(list(request_dir.glob("*.json")))
        request = ApprovalRequest(
            request_id=f"apr-{seq:04d}",
            run_id=run_id,
            agent_id=agent_id,
            tool=tool,
            args_hash=args_hash(arguments),
            capability=capability,
            reason=reason,
            requested_at=now,
            expires_at=now + timeout,
            step=step,
        )
        path = request_dir / f"{request.request_id}.json"
        request.path = path
        # 原子写：临时文件 + rename，避免读到半个文件
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps(request.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(tmp, path)
        return request

    # -- 等待 -------------------------------------------------------------

    def wait_for_decision(
        self, request: ApprovalRequest
    ) -> tuple[bool, str]:
        """阻塞等待审批决定。

        Returns:
            ``(是否批准, 原因)``。超时按拒绝处理。
        """
        if request.path is None:
            return False, "审批请求未落盘"
        deadline = min(
            time.monotonic() + max(0.0, self.timeout_seconds),
            request.expires_at,
        )
        while True:
            data = self._read(request.path)
            if data is not None:
                status = data.get("status", "pending")
                if status == "approved":
                    return True, data.get("reason", "")
                if status == "rejected":
                    return False, data.get("reason", "审批被拒")
            if time.monotonic() >= deadline:
                self._mark_expired(request)
                return False, "审批超时"
            self._sleep(self.poll_interval)

    def _read(self, path: Path) -> dict[str, Any] | None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None

    def _mark_expired(self, request: ApprovalRequest) -> None:
        if request.path is None:
            return
        data = self._read(request.path) or request.to_dict()
        data["status"] = "expired"
        data["decided_at"] = time.time()
        tmp = request.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, request.path)

    # -- 对外入口 ---------------------------------------------------------

    def request(
        self,
        ctx: Any,
        tool: str,
        arguments: dict[str, Any],
        *,
        spec: Any = None,
    ) -> tuple[bool, str]:
        """发起审批并等待决定。返回 ``(是否批准, 原因)``。

        审批**只对这一组参数有效**（§7.5.1）：决定后重算参数哈希，
        与落盘请求里的 `args_hash` 不一致 → 审批失效（拒绝）。
        """
        capability = getattr(spec, "capability", "write")
        timeout = self._policy_timeout(ctx) or self.timeout_seconds
        step = self._current_step_id(ctx)
        try:
            request = self.create_request(
                run_id=ctx.run_id,
                agent_id=self.policy_agent_id(ctx),
                tool=tool,
                arguments=arguments,
                capability=capability,
                reason=f"{capability} 工具需人工审批",
                timeout_seconds=timeout,
                step=step,
            )
        except OSError as exc:
            # 落盘失败 → fail-closed
            return False, f"审批请求落盘失败：{exc}"
        approved, reason = self.wait_for_decision(request)
        if not approved:
            return False, reason
        # 参数绑定复核：审批期间参数被改动 → 审批失效
        current = self._read(request.path) if request.path else None
        if current is None:
            return False, "审批记录不可读，按拒绝处理（fail-closed）"
        recorded = current.get("args_hash", "")
        if recorded and recorded != args_hash(arguments):
            return False, "参数在审批期间发生变化，审批失效（需重新审批）"
        return True, reason

    @staticmethod
    def _policy_timeout(ctx: Any) -> int:
        """审批等待超时：治理块 `limits.approval_timeout_seconds` 优先。"""
        policy = getattr(ctx, "policy", None)
        limits = getattr(policy, "limits", None)
        timeout = getattr(limits, "approval_timeout_seconds", None)
        return int(timeout) if timeout else 0

    @staticmethod
    def _current_step_id(ctx: Any) -> str | None:
        current = getattr(ctx, "current_step", None)
        step = current() if callable(current) else None
        return getattr(step, "id", None)

    @staticmethod
    def policy_agent_id(ctx: Any) -> str:
        policy = getattr(ctx, "policy", None)
        return getattr(policy, "agent_id", "")

    # -- 决定（CLI / UI 调用）---------------------------------------------

    def decide(
        self,
        request_id: str,
        *,
        approved: bool,
        actor: str = "",
        reason: str = "",
        run_id: str | None = None,
    ) -> bool:
        """批准或拒绝一个请求（CLI `governance approve/reject` 与客户端 UI 共用）。

        过期请求不可再批准——审批请求只在 `expires_at` 前有效（§7.5.2）。
        """
        paths = self._find_request(request_id, run_id)
        if not paths:
            return False
        path = paths[0]
        data = self._read(path) or {}
        if approved:
            expires_at = float(data.get("expires_at", 0.0) or 0.0)
            if expires_at and time.time() > expires_at:
                return False
        data["status"] = "approved" if approved else "rejected"
        data["decided_by"] = actor
        data["reason"] = reason
        data["decided_at"] = time.time()
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)
        return True

    def _find_request(self, request_id: str, run_id: str | None) -> list[Path]:
        root = self.control_dir / "approvals"
        if run_id:
            return list((root / run_id).glob(f"{request_id}.json"))
        return list(root.glob(f"*/{request_id}.json"))

    def list_pending(self, run_id: str | None = None) -> list[ApprovalRequest]:
        """列出待审批请求。"""
        root = self.control_dir / "approvals"
        paths = (
            list((root / run_id).glob("*.json")) if run_id else list(root.glob("*/*.json"))
        )
        requests = []
        for path in sorted(paths):
            data = self._read(path)
            if data and data.get("status") == "pending":
                requests.append(ApprovalRequest.from_dict(data, path))
        return requests
