# 08 - 安全设计

## 概述

安全是 Harness 设计的核心考量。作为可内嵌的 Agent 框架，Harness 需要在提供强大能力的同时，确保系统安全可控。

## 安全架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Security Layers                          │
│                                                              │
│  Layer 1: 输入验证                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • Prompt Injection 检测                              │   │
│  │ • 输入长度限制                                       │   │
│  │ • 恶意模式检测                                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                   │
│  Layer 2: 权限控制                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • 工具权限管理                                       │   │
│  │ • 路径访问控制                                       │   │
│  │ • 命令执行限制                                       │   │
│  │ • 操作确认机制                                       │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                   │
│  Layer 3: 执行隔离                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • 沙箱执行环境                                       │   │
│  │ • 资源限制（CPU/内存/时间）                          │   │
│  │ • 网络隔离                                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓                                   │
│  Layer 4: 审计日志                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ • 所有操作记录                                       │   │
│  │ • 工具调用追踪                                       │   │
│  │ • 异常检测                                           │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 权限模型

### Permission Level

```python
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Set
from pathlib import Path

class PermissionLevel(Enum):
    """权限级别"""
    SAFE = "safe"              # 安全操作，自动允许
    MODERATE = "moderate"      # 中等风险，可选确认
    DANGEROUS = "dangerous"    # 危险操作，必须确认
    RESTRICTED = "restricted"  # 受限操作，默认禁用

class PermissionMode(Enum):
    """权限模式"""
    FULL = "full"              # 完全访问
    ASK = "ask"                # 询问确认
    SANDBOX = "sandbox"        # 沙箱模式
    READ_ONLY = "read_only"    # 只读模式
```

### PermissionSet

```python
@dataclass
class PermissionSet:
    """权限集合"""

    # 路径权限
    allowed_paths: List[str] = field(default_factory=list)
    blocked_paths: List[str] = field(default_factory=list)
    read_only_paths: List[str] = field(default_factory=list)

    # 命令权限
    allowed_commands: List[str] = field(default_factory=list)
    blocked_commands: List[str] = field(default_factory=list)
    command_whitelist_mode: bool = False  # True = 白名单模式

    # 工具权限
    allowed_tools: Set[str] = field(default_factory=set)
    blocked_tools: Set[str] = field(default_factory=set)

    # 网络权限
    allowed_domains: List[str] = field(default_factory=list)
    blocked_domains: List[str] = field(default_factory=list)
    allow_all_network: bool = True

    # 资源限制
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    max_execution_time: float = 60.0       # 秒
    max_memory_mb: int = 512               # MB

    # 默认策略
    default_deny: bool = True

    def is_path_allowed(self, path: str, action: str = "read") -> bool:
        """检查路径访问权限"""
        try:
            abs_path = Path(path).resolve()
        except Exception:
            return False

        # 检查黑名单
        for blocked in self.blocked_paths:
            try:
                if abs_path.is_relative_to(Path(blocked).expanduser().resolve()):
                    return False
            except Exception:
                continue

        # 检查只读路径
        if action == "write":
            for read_only in self.read_only_paths:
                try:
                    if abs_path.is_relative_to(Path(read_only).expanduser().resolve()):
                        return False
                except Exception:
                    continue

        # 检查白名单
        if self.allowed_paths:
            for allowed in self.allowed_paths:
                try:
                    if abs_path.is_relative_to(Path(allowed).expanduser().resolve()):
                        return True
                except Exception:
                    continue
            return False

        return not self.default_deny

    def is_command_allowed(self, command: str) -> bool:
        """检查命令执行权限"""
        # 检查黑名单
        for blocked in self.blocked_commands:
            if blocked in command:
                return False

        # 白名单模式
        if self.command_whitelist_mode:
            for allowed in self.allowed_commands:
                if command.strip().startswith(allowed):
                    return True
            return False

        return True

    def is_tool_allowed(self, tool_name: str) -> bool:
        """检查工具使用权限"""
        if tool_name in self.blocked_tools:
            return False
        if self.allowed_tools and tool_name not in self.allowed_tools:
            return False
        return True

    def is_domain_allowed(self, domain: str) -> bool:
        """检查网络域名权限"""
        if domain in self.blocked_domains:
            return False
        if self.allowed_domains and domain not in self.allowed_domains:
            return False
        return self.allow_all_network

    @classmethod
    def sandbox(cls, workspace: str) -> "PermissionSet":
        """创建沙箱权限"""
        return cls(
            allowed_paths=[workspace],
            blocked_paths=[
                "/etc", "/root", "/home",
                "~/.ssh", "~/.gnupg", "~/.config",
                "~/.aws", "~/.env"
            ],
            blocked_commands=[
                "rm -rf", "sudo", "chmod", "chown",
                "mkfs", "dd", "fdisk",
                "curl | bash", "wget | bash",
                "> /dev/", "2>&1"
            ],
            allowed_tools={"read", "write", "edit", "glob", "grep"},
            blocked_tools={"bash"},
            allow_all_network=False,
            default_deny=True,
            max_execution_time=30.0
        )

    @classmethod
    def read_only(cls, workspace: str) -> "PermissionSet":
        """创建只读权限"""
        permissions = cls.sandbox(workspace)
        permissions.read_only_paths = [workspace]
        permissions.allowed_tools = {"read", "glob", "grep"}
        return permissions

    @classmethod
    def full_access(cls) -> "PermissionSet":
        """创建完全访问权限（谨慎使用）"""
        return cls(
            blocked_commands=["rm -rf /", "rm -rf ~"],
            default_deny=False,
            allow_all_network=True
        )
```

## 沙箱执行

### Sandbox Executor

```python
import asyncio
import subprocess
import resource
import os
from typing import Optional, Dict, Any

class SandboxExecutor:
    """沙箱执行器"""

    def __init__(
        self,
        permissions: PermissionSet,
        container_runtime: str = "none"  # none, docker, nsjail
    ):
        self.permissions = permissions
        self.container_runtime = container_runtime

    async def execute_command(
        self,
        command: str,
        cwd: str = None,
        env: Dict[str, str] = None,
        stdin: str = None
    ) -> "ExecutionResult":
        """在沙箱中执行命令"""

        # 权限检查
        if not self.permissions.is_command_allowed(command):
            raise PermissionDeniedError(f"Command not allowed: {command}")

        # 根据运行时选择执行方式
        if self.container_runtime == "docker":
            return await self._execute_docker(command, cwd, env, stdin)
        elif self.container_runtime == "nsjail":
            return await self._execute_nsjail(command, cwd, env, stdin)
        else:
            return await self._execute_native(command, cwd, env, stdin)

    async def _execute_native(
        self,
        command: str,
        cwd: str,
        env: Dict[str, str],
        stdin: str
    ) -> "ExecutionResult":
        """原生执行（有限隔离）"""

        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE if stdin else None,
            cwd=cwd,
            env=self._filter_env(env)
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(stdin.encode() if stdin else None),
                timeout=self.permissions.max_execution_time
            )

            return ExecutionResult(
                exit_code=process.returncode,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace")
            )

        except asyncio.TimeoutError:
            process.kill()
            raise TimeoutError(f"Execution timed out after {self.permissions.max_execution_time}s")

    async def _execute_docker(
        self,
        command: str,
        cwd: str,
        env: Dict[str, str],
        stdin: str
    ) -> "ExecutionResult":
        """Docker 容器执行"""

        # 构建 docker 命令
        docker_cmd = [
            "docker", "run", "--rm",
            "--network", "none" if not self.permissions.allow_all_network else "bridge",
            "--memory", f"{self.permissions.max_memory_mb}m",
            "--cpus", "1",
            "-v", f"{cwd}:/workspace",
            "-w", "/workspace",
        ]

        # 添加环境变量
        for key, value in (env or {}).items():
            docker_cmd.extend(["-e", f"{key}={value}"])

        # 使用安全镜像
        docker_cmd.extend(["harness-sandbox:latest", "sh", "-c", command])

        process = await asyncio.create_subprocess_exec(
            *docker_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.PIPE if stdin else None
        )

        stdout, stderr = await process.communicate(
            stdin.encode() if stdin else None
        )

        return ExecutionResult(
            exit_code=process.returncode,
            stdout=stdout.decode("utf-8", errors="replace"),
            stderr=stderr.decode("utf-8", errors="replace")
        )

    def _filter_env(self, env: Dict[str, str] = None) -> Dict[str, str]:
        """过滤环境变量，移除敏感信息"""
        sensitive_vars = {
            "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY",
            "ANTHROPIC_API_KEY", "OPENAI_API_KEY",
            "GITHUB_TOKEN", "GITLAB_TOKEN",
            "DATABASE_URL", "DB_PASSWORD"
        }

        filtered = dict(os.environ)
        for var in sensitive_vars:
            filtered.pop(var, None)

        if env:
            filtered.update(env)

        return filtered


@dataclass
class ExecutionResult:
    """执行结果"""
    exit_code: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        return self.exit_code == 0
```

## 输入验证

### Prompt Injection 检测

```python
import re
from typing import List, Tuple

class PromptInjectionDetector:
    """Prompt 注入检测器"""

    # 常见的注入模式
    INJECTION_PATTERNS = [
        # 角色扮演
        r"ignore (all )?(previous|above) instructions",
        r"disregard (all )?(previous|above) instructions",
        r"forget (all )?(previous|above) instructions",

        # 系统提示泄露
        r"what (is|are) your (system |initial )?instructions",
        r"repeat your (system |initial )?prompt",
        r"show me your (system |initial )?prompt",

        # 越狱尝试
        r"you are now (a|an) \w+",
        r"pretend (to be|you are)",
        r"act as (if|though)",

        # 编码绕过
        r"base64",
        r"rot13",
        r"hex encode",

        # 危险指令
        r"sudo",
        r"chmod",
        r"rm -rf",
        r"delete all",
        r"format disk",
    ]

    def __init__(self, custom_patterns: List[str] = None):
        self.patterns = [
            re.compile(p, re.IGNORECASE)
            for p in self.INJECTION_PATTERNS
        ]
        if custom_patterns:
            self.patterns.extend(
                re.compile(p, re.IGNORECASE)
                for p in custom_patterns
            )

    def detect(self, text: str) -> Tuple[bool, List[str]]:
        """
        检测是否存在注入尝试

        Returns:
            (is_safe, detected_patterns)
        """
        detected = []

        for pattern in self.patterns:
            if pattern.search(text):
                detected.append(pattern.pattern)

        return len(detected) == 0, detected

    def sanitize(self, text: str) -> str:
        """清理可疑内容"""
        # 基本清理：转义特殊字符
        sanitized = text

        # 可以添加更复杂的清理逻辑
        # 注意：清理并不能保证安全，应该结合拒绝策略

        return sanitized


class InputValidator:
    """输入验证器"""

    def __init__(
        self,
        max_length: int = 100000,
        check_injection: bool = True
    ):
        self.max_length = max_length
        self.injection_detector = PromptInjectionDetector() if check_injection else None

    def validate(self, text: str) -> "ValidationResult":
        """验证输入"""
        errors = []
        warnings = []

        # 长度检查
        if len(text) > self.max_length:
            errors.append(f"Input exceeds maximum length ({self.max_length})")

        # 注入检测
        if self.injection_detector:
            is_safe, patterns = self.injection_detector.detect(text)
            if not is_safe:
                warnings.append(f"Potential injection patterns detected: {patterns}")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            sanitized_text=self.injection_detector.sanitize(text) if self.injection_detector else text
        )


@dataclass
class ValidationResult:
    """验证结果"""
    valid: bool
    errors: List[str]
    warnings: List[str]
    sanitized_text: str
```

## 操作确认

```python
from abc import ABC, abstractmethod
from typing import Callable, Optional
import asyncio

class ConfirmationHandler(ABC):
    """确认处理器抽象"""

    @abstractmethod
    async def request_confirmation(
        self,
        operation: str,
        details: Dict[str, Any],
        risk_level: str
    ) -> bool:
        """请求用户确认"""
        pass


class ConsoleConfirmation(ConfirmationHandler):
    """控制台确认"""

    async def request_confirmation(
        self,
        operation: str,
        details: Dict[str, Any],
        risk_level: str
    ) -> bool:
        print(f"\n[CONFIRMATION REQUIRED] Risk: {risk_level}")
        print(f"Operation: {operation}")
        print(f"Details: {details}")
        print()

        response = input("Proceed? [y/N]: ")
        return response.lower() == "y"


class CallbackConfirmation(ConfirmationHandler):
    """回调确认"""

    def __init__(self, callback: Callable[[str, Dict, str], bool]):
        self.callback = callback

    async def request_confirmation(
        self,
        operation: str,
        details: Dict[str, Any],
        risk_level: str
    ) -> bool:
        if asyncio.iscoroutinefunction(self.callback):
            return await self.callback(operation, details, risk_level)
        return self.callback(operation, details, risk_level)


class ConfirmationManager:
    """确认管理器"""

    def __init__(
        self,
        handler: ConfirmationHandler,
        auto_approve_safe: bool = True,
        cache_approvals: bool = False
    ):
        self.handler = handler
        self.auto_approve_safe = auto_approve_safe
        self.cache_approvals = cache_approvals
        self._approval_cache: Dict[str, bool] = {}

    async def check_confirmation(
        self,
        tool: Tool,
        arguments: Dict[str, Any]
    ) -> bool:
        """检查是否需要确认并请求"""

        # 安全操作自动批准
        if self.auto_approve_safe and tool.permission_level == PermissionLevel.SAFE:
            return True

        # 检查缓存
        cache_key = f"{tool.name}:{json.dumps(arguments, sort_keys=True)}"
        if self.cache_approvals and cache_key in self._approval_cache:
            return self._approval_cache[cache_key]

        # 请求确认
        risk_level = tool.permission_level.value
        approved = await self.handler.request_confirmation(
            operation=tool.name,
            details=arguments,
            risk_level=risk_level
        )

        # 缓存结果
        if self.cache_approvals:
            self._approval_cache[cache_key] = approved

        return approved
```

## 审计日志

```python
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import hashlib

@dataclass
class AuditLogEntry:
    """审计日志条目"""
    timestamp: datetime
    session_id: str
    event_type: str              # tool_call, file_access, command, etc.
    action: str
    resource: str
    arguments: Dict[str, Any]
    result: str                  # success, denied, error
    details: Dict[str, Any]

    def to_json(self) -> str:
        return json.dumps({
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "event_type": self.event_type,
            "action": self.action,
            "resource": self.resource,
            "arguments": self._sanitize_arguments(self.arguments),
            "result": self.result,
            "details": self.details
        })

    def _sanitize_arguments(self, args: Dict) -> Dict:
        """清理敏感参数"""
        sensitive_keys = {"password", "token", "secret", "key", "credential"}
        sanitized = {}
        for k, v in args.items():
            if any(s in k.lower() for s in sensitive_keys):
                sanitized[k] = "***REDACTED***"
            else:
                sanitized[k] = v
        return sanitized


class AuditLogger:
    """审计日志器"""

    def __init__(
        self,
        log_dir: str = "~/.harness/audit",
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        retention_days: int = 30
    ):
        self.log_dir = Path(log_dir).expanduser()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size = max_file_size
        self.retention_days = retention_days
        self._current_file: Optional[Path] = None

    def log(self, entry: AuditLogEntry):
        """记录审计日志"""
        log_file = self._get_log_file()

        with open(log_file, "a") as f:
            f.write(entry.to_json() + "\n")

    def _get_log_file(self) -> Path:
        """获取当前日志文件"""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"audit-{today}.log"

        # 检查文件大小
        if log_file.exists() and log_file.stat().st_size > self.max_file_size:
            # 创建新文件
            index = 1
            while True:
                new_file = self.log_dir / f"audit-{today}-{index}.log"
                if not new_file.exists():
                    log_file = new_file
                    break
                index += 1

        return log_file

    def query(
        self,
        session_id: str = None,
        event_type: str = None,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> List[AuditLogEntry]:
        """查询审计日志"""
        results = []

        for log_file in self.log_dir.glob("audit-*.log"):
            with open(log_file) as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        entry = AuditLogEntry(
                            timestamp=datetime.fromisoformat(data["timestamp"]),
                            session_id=data["session_id"],
                            event_type=data["event_type"],
                            action=data["action"],
                            resource=data["resource"],
                            arguments=data["arguments"],
                            result=data["result"],
                            details=data["details"]
                        )

                        # 过滤
                        if session_id and entry.session_id != session_id:
                            continue
                        if event_type and entry.event_type != event_type:
                            continue
                        if start_time and entry.timestamp < start_time:
                            continue
                        if end_time and entry.timestamp > end_time:
                            continue

                        results.append(entry)
                    except Exception:
                        continue

        return sorted(results, key=lambda e: e.timestamp, reverse=True)

    def cleanup_old_logs(self):
        """清理过期日志"""
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=self.retention_days)

        for log_file in self.log_dir.glob("audit-*.log"):
            try:
                file_date_str = log_file.stem.split("-")[1]
                file_date = datetime.strptime(file_date_str, "%Y-%m-%d")

                if file_date < cutoff:
                    log_file.unlink()
            except Exception:
                continue
```

## 安全配置

```python
@dataclass
class SecurityConfig:
    """安全配置"""

    # 权限模式
    permission_mode: PermissionMode = PermissionMode.SANDBOX

    # 路径配置
    allowed_paths: List[str] = field(default_factory=list)
    blocked_paths: List[str] = field(default_factory=lambda: [
        "/etc", "/root", "~/.ssh", "~/.aws", "~/.config"
    ])

    # 命令配置
    blocked_commands: List[str] = field(default_factory=lambda: [
        "rm -rf /", "rm -rf ~", "sudo", "chmod -R 777"
    ])

    # 工具配置
    allowed_tools: List[str] = field(default_factory=list)  # 空 = 全部允许
    blocked_tools: List[str] = field(default_factory=list)

    # 网络配置
    allow_network: bool = True
    allowed_domains: List[str] = field(default_factory=list)
    blocked_domains: List[str] = field(default_factory=list)

    # 执行限制
    max_execution_time: float = 60.0
    max_file_size: int = 10 * 1024 * 1024
    max_memory_mb: int = 512

    # 确认配置
    require_confirmation: bool = True
    auto_approve_safe: bool = True
    cache_approvals: bool = False

    # 输入验证
    max_input_length: int = 100000
    check_prompt_injection: bool = True

    # 审计
    enable_audit_log: bool = True
    audit_log_dir: str = "~/.harness/audit"
    audit_retention_days: int = 30

    # 沙箱
    sandbox_runtime: str = "none"  # none, docker, nsjail

    def to_permission_set(self) -> PermissionSet:
        """转换为权限集合"""
        return PermissionSet(
            allowed_paths=self.allowed_paths,
            blocked_paths=self.blocked_paths,
            blocked_commands=self.blocked_commands,
            allowed_tools=set(self.allowed_tools),
            blocked_tools=set(self.blocked_tools),
            allow_all_network=self.allow_network,
            allowed_domains=self.allowed_domains,
            blocked_domains=self.blocked_domains,
            max_execution_time=self.max_execution_time,
            max_file_size=self.max_file_size,
            max_memory_mb=self.max_memory_mb
        )


# 预设配置
SECURITY_PRESETS = {
    "development": SecurityConfig(
        permission_mode=PermissionMode.ASK,
        require_confirmation=False,
        sandbox_runtime="none"
    ),

    "production": SecurityConfig(
        permission_mode=PermissionMode.SANDBOX,
        sandbox_runtime="docker",
        require_confirmation=True,
        enable_audit_log=True
    ),

    "readonly": SecurityConfig(
        permission_mode=PermissionMode.READ_ONLY,
        allowed_tools=["read", "glob", "grep"],
        blocked_tools=["write", "edit", "bash"]
    ),

    "isolated": SecurityConfig(
        permission_mode=PermissionMode.SANDBOX,
        sandbox_runtime="docker",
        allow_network=False,
        allowed_paths=["/workspace"],
        blocked_commands=["rm", "sudo", "chmod"]
    )
}
```

## 安全最佳实践

### 1. 始终使用最小权限原则

```python
# 好：明确限制工作目录
agent = AgentHarness(
    security=SecurityConfig(
        permission_mode=PermissionMode.SANDBOX,
        allowed_paths=["/workspace/my-project"]
    )
)

# 避免：完全访问权限
agent = AgentHarness(
    security=SecurityConfig(
        permission_mode=PermissionMode.FULL  # 危险！
    )
)
```

### 2. 启用审计日志

```python
agent = AgentHarness(
    security=SecurityConfig(
        enable_audit_log=True,
        audit_log_dir="/var/log/harness"
    )
)
```

### 3. 验证用户输入

```python
validator = InputValidator(check_injection=True)

user_input = get_user_input()
result = validator.validate(user_input)

if not result.valid:
    raise ValueError(result.errors)

if result.warnings:
    log.warning(f"Input warnings: {result.warnings}")
```

### 4. 使用沙箱执行

```python
# 生产环境推荐使用 Docker 沙箱
agent = AgentHarness(
    security=SecurityConfig(
        sandbox_runtime="docker",
        max_execution_time=30.0
    )
)
```

### 5. 定期审查审计日志

```python
# 检查可疑活动
audit = AuditLogger()
suspicious = audit.query(
    event_type="tool_call",
    start_time=datetime.now() - timedelta(days=1)
)

for entry in suspicious:
    if entry.result == "denied":
        alert_security_team(entry)
```