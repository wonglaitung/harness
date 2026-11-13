"""运维期诊断命令（M6-dep）。

``harness doctor --deps`` 审计已安装依赖的已知漏洞（调用 ``uv pip audit``
或 ``pip-audit``）。CLI 本身不内置 CVE 数据库——交给平台审计器，修复仍是
部署侧的人审工作。
"""

from __future__ import annotations

import shutil
import subprocess


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
