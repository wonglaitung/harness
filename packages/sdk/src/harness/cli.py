"""Minimal CLI for the Harness SDK.

M6-dep: ships a ``harness doctor --deps`` command that audits the installed
dependency tree for known vulnerabilities (via ``uv pip audit`` or
``pip-audit``). The SDK keeps no built-in CVE database — it delegates to the
platform auditor so remediation stays a human-reviewed, deploy-side concern.

Example:
    harness doctor --deps
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys


def doctor_deps() -> int:
    """Audit dependencies for known CVEs.

    Returns an int exit code suitable for ``sys.exit``.
    """
    if shutil.which("uv"):
        cmd = ["uv", "pip", "audit"]
    elif shutil.which("pip-audit"):
        cmd = ["pip-audit"]
    else:
        print(
            "No dependency auditor found. Install 'uv' or 'pip-audit' to run "
            "dependency CVE checks (harness does not bundle a CVE database)."
        )
        return 1
    try:
        return subprocess.call(cmd)
    except FileNotFoundError:
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="harness", description="Harness SDK CLI")
    sub = parser.add_subparsers(dest="command")
    doctor = sub.add_parser("doctor", help="Run diagnostics")
    doctor.add_argument(
        "--deps", action="store_true", help="Audit dependencies for known CVEs"
    )
    args = parser.parse_args(argv)
    if args.command == "doctor":
        if args.deps:
            return doctor_deps()
        parser.print_help()
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
