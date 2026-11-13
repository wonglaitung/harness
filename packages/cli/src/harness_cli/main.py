"""``harness`` 命令入口：argparse + 分发。

治理的强制力在 SDK 运行时（``AgentHarness`` + ``GovernanceGateway``）；
本包提供创作期（生成/校验治理块、LLM 初稿）与运维期（审批、Kill Switch、
诊断）命令。`init` / `check` / 审批 / 控制命令是确定性代码；只有 `draft`
显式调用 LLM，且输出必须通过与 `check` 同源的校验。
"""

from __future__ import annotations

import argparse

from harness_cli.doctor import doctor_deps
from harness_cli.draft import governance_draft
from harness_cli.governance import (
    governance_check,
    governance_control,
    governance_decide,
    governance_init,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="harness", description="Harness SDK CLI")
    sub = parser.add_subparsers(dest="command")

    doctor = sub.add_parser("doctor", help="Run diagnostics")
    doctor.add_argument(
        "--deps", action="store_true", help="Audit dependencies for known CVEs"
    )

    governance = sub.add_parser("governance", help="治理块与运行期治理")
    gov = governance.add_subparsers(dest="governance_command")

    init = gov.add_parser(
        "init",
        help="迁移工具：生成并写入治理块（默认写入，--dry-run 预览）",
    )
    init.add_argument("skill", help="技能文件或目录（递归扫描有 frontmatter 的 .md）")
    init.add_argument(
        "--agent-id",
        default=None,
        help="治理身份；缺省取 HARNESS_GOVERNANCE_AGENT_ID，再缺省取技能名",
    )
    init.add_argument("--dry-run", action="store_true", help="只预览，不写文件")

    check = gov.add_parser("check", help="校验治理块（29 条规则）")
    check.add_argument("skill", help="技能文件路径")

    draft = gov.add_parser(
        "draft",
        help="用 LLM 基于技能正文生成治理块初稿（需人工确认）",
    )
    draft.add_argument("skill", help="技能文件或目录（递归扫描有 frontmatter 的 .md）")
    draft.add_argument(
        "--agent-id",
        default=None,
        help="治理身份；缺省取 HARNESS_GOVERNANCE_AGENT_ID，再缺省取技能名",
    )
    draft.add_argument("--dry-run", action="store_true", help="只预览，不写文件")
    draft.add_argument(
        "--emit-prompt",
        action="store_true",
        help="只输出提示词，不调用模型、不写文件",
    )
    draft.add_argument(
        "--provider",
        default=None,
        help=(
            "LLM provider：openai / anthropic"
            "（缺省读 HARNESS_LLM_PROVIDER / HARNESS_PROVIDER，再缺省 openai）"
        ),
    )
    draft.add_argument(
        "--model",
        default=None,
        help="模型名（缺省读 HARNESS_LLM_MODEL / HARNESS_MODEL，再取 provider 默认模型）",
    )
    draft.add_argument(
        "--base-url",
        default=None,
        help="OpenAI 兼容端点（缺省读 HARNESS_LLM_BASE_URL / HARNESS_BASE_URL / OPENAI_BASE_URL）",
    )
    draft.add_argument("--timeout", type=float, default=120.0, help="调用超时秒数")

    for name, help_text in (("approve", "批准审批请求"), ("reject", "拒绝审批请求")):
        decide = gov.add_parser(name, help=help_text)
        decide.add_argument("request_id", help="审批请求 id（如 apr-0001）")
        decide.add_argument("--actor", default="", help="操作人（自由文本）")
        decide.add_argument("--reason", default="", help="原因")
        decide.add_argument("--run-id", default=None, help="限定 run（可选）")

    for name, help_text in (
        ("suspend", "暂停 Agent"),
        ("resume", "恢复 Agent"),
        ("status", "查看 Agent 控制状态"),
    ):
        control = gov.add_parser(name, help=help_text)
        control.add_argument("agent_id", help="治理身份 agent_id")
        control.add_argument("--reason", default="", help="原因")
        control.add_argument("--actor", default="", help="操作人（自由文本）")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "doctor":
        if args.deps:
            return doctor_deps()
        parser.print_help()
        return 0

    if args.command == "governance":
        action = args.governance_command
        if action == "init":
            return governance_init(
                args.skill,
                agent_id=args.agent_id,
                dry_run=args.dry_run,
            )
        if action == "check":
            return governance_check(args.skill)
        if action == "draft":
            return governance_draft(
                args.skill,
                agent_id=args.agent_id,
                dry_run=args.dry_run,
                emit_prompt=args.emit_prompt,
                provider=args.provider,
                model=args.model,
                base_url=args.base_url,
                timeout=args.timeout,
            )
        if action in ("approve", "reject"):
            return governance_decide(
                args.request_id,
                approved=action == "approve",
                actor=args.actor,
                reason=args.reason,
                run_id=args.run_id,
            )
        if action in ("suspend", "resume", "status"):
            return governance_control(
                args.agent_id,
                action,
                reason=args.reason,
                actor=args.actor,
            )
        parser.parse_args(["governance", "--help"])
        return 0

    parser.print_help()
    return 0
