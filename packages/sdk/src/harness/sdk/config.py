"""Configuration classes for Harness SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from harness.model_presets import get_default_output_tokens, get_model_preset, parse_context_window


@dataclass
class SecurityConfig:
    """
    Security configuration for the agent.

    Controls input validation, output sanitization, audit logging, and sandbox execution.
    """

    # Input validation
    enable_input_validation: bool = True
    max_input_length: int = 100000
    check_prompt_injection: bool = True

    # Output sanitization
    enable_output_sanitization: bool = True
    max_output_length: int = 100000

    # Audit logging
    enable_audit_log: bool = True
    audit_log_dir: str = "~/.harness/audit"
    audit_retention_days: int = 30

    # Sandbox settings
    enable_sandbox: bool = True
    sandbox_max_execution_time: float = 30.0
    sandbox_max_output_size: int = 1_000_000  # 1MB
    sandbox_blocked_commands: list[str] = field(default_factory=lambda: [
        "rm -rf /",
        "rm -rf ~",
        "sudo",
        "chmod -R 777",
        "mkfs",
        "dd if=",
        "> /dev/",
        ":(){ :|:& };:",  # Fork bomb
    ])
    sandbox_blocked_patterns: list[str] = field(default_factory=lambda: [
        "rm -rf",
        "sudo",
        "chmod",
        "chown",
        "mkfs",
        "dd if=",
        "curl | bash",
        "wget | bash",
    ])
    sandbox_allowed_commands: list[str] | None = None  # None = allow all non-blocked
    sandbox_allowed_env_vars: list[str] = field(default_factory=lambda: [
        "PATH", "HOME", "USER", "LANG", "LC_ALL", "TERM",
    ])


@dataclass
class CostControlConfig:
    """
    Cost control configuration for budget management.

    Supports multi-level budget control:
    - Session level: tokens, tool calls, iterations
    - User level: daily tokens, hourly requests
    - Global level: daily budget in USD
    """

    # Session level
    max_tokens_per_session: int = 1_000_000
    max_tool_calls_per_session: int = 500
    max_iterations_per_request: int = 20

    # User level
    daily_token_limit: int = 10_000_000
    hourly_request_limit: int = 100

    # Global level
    global_daily_budget_usd: float = 100.0
    auto_throttle: bool = True
    fallback_model: str | None = None
    context_reduction_ratio: float = 0.5

    # Warning threshold (0.0 - 1.0)
    warning_threshold: float = 0.8


@dataclass
class ObservabilityConfig:
    """
    Observability configuration for OpenTelemetry integration.

    Supports tracing to Jaeger, Datadog, Langfuse, and other
    OTel-compatible backends.
    """

    enabled: bool = False
    service_name: str = "harness-agent"
    service_version: str = "0.1.0"
    export_console: bool = False
    export_otlp: bool = False
    otlp_endpoint: str = "http://localhost:4317"
    sample_rate: float = 1.0


@dataclass
class OffloadConfig:
    """
    Configuration for tool output offloading.

    When tool outputs are too large, they can be offloaded to temporary files
    to keep context windows manageable. Files are stored in .harness/offload
    within the current working directory, ensuring sandbox access.

    Attributes:
        enabled: Whether to enable output offloading
        size_threshold_chars: Minimum output size to trigger offload
        preview_length: Length of preview to keep in context
    """

    enabled: bool = True
    size_threshold_chars: int = 50000  # Offload only very large outputs (50K chars)
    preview_length: int = 500  # Keep more context in preview


@dataclass
class StorageConfig:
    """
    Session storage configuration.

    Supports file-based or SQLite storage.
    """

    # Storage type: "file" or "sqlite"
    type: Literal["file", "sqlite"] = "file"

    # For file storage
    storage_dir: str = ".harness/sessions"

    # For SQLite storage
    sqlite_path: str = ".harness/harness.db"

    # Async mode (only for SQLite)
    async_mode: bool = True

    # Connection pool size (only for async SQLite)
    pool_size: int = 5


@dataclass
class HarnessConfig:
    """
    Main configuration for AgentHarness.

    Provides a simple way to configure the agent without
    building each component manually.
    """

    # LLM settings
    model: str = "claude-sonnet-4-6"
    api_key: str | None = None
    provider: str = "auto"  # "anthropic", "openai", "auto" for auto-detect
    base_url: str | None = None  # For custom endpoints (e.g., local LLM, Azure)

    # Compatibility settings
    tool_result_role: str = "tool"  # "tool" (native) or "user" (compatibility mode for proxy APIs)

    # Context settings (new)
    context_window: int | str = "auto"  # "auto", "32k", "64k", "128k", "200k", or int
    max_tokens: int | str = "auto"  # Output tokens: "auto" or int
    temperature: float = 1.0

    # Memory settings
    memory_dir: str = ".harness/memory"
    session_window: int = 100  # Keep more messages for larger context

    # Tool settings
    sandbox_workspace: str | None = None
    enable_network: bool = False

    # Loop settings
    max_iterations: int = 100
    tool_timeout: float = 30.0

    # Optional settings
    system_prompt: str = ""  # If empty, no system prompt is sent (uses model's default behavior)
    extra_config: dict[str, Any] = field(default_factory=dict)

    # Security settings
    security: SecurityConfig | None = None

    # Cost control settings
    cost_control: CostControlConfig | None = None

    # Observability settings
    observability: ObservabilityConfig | None = None

    # Storage settings
    storage: StorageConfig | None = None

    # Offload settings
    offload: OffloadConfig | None = None

    # Resolved values (set in __post_init__)
    _context_window: int = field(default=0, repr=False)
    _max_tokens: int = field(default=0, repr=False)

    def __post_init__(self) -> None:
        """Resolve auto values based on model preset."""
        # Resolve context_window
        self._context_window = parse_context_window(self.context_window, self.model)

        # Resolve max_tokens (output)
        if isinstance(self.max_tokens, str) and self.max_tokens.lower() == "auto":
            self._max_tokens = get_default_output_tokens(self.model)
        elif isinstance(self.max_tokens, int):
            self._max_tokens = self.max_tokens
        else:
            self._max_tokens = get_default_output_tokens(self.model)

        # Auto-detect provider if needed
        if self.provider == "auto":
            preset = get_model_preset(self.model)
            self.provider = preset.provider

    def get_context_window(self) -> int:
        """Get resolved context window size."""
        return self._context_window

    def get_max_tokens(self) -> int:
        """Get resolved output token limit."""
        return self._max_tokens

    @classmethod
    def from_file(cls, path: str) -> "HarnessConfig":
        """Load configuration from YAML or JSON file."""
        import json

        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        content = file_path.read_text()

        if file_path.suffix in (".yaml", ".yml"):
            try:
                import yaml

                data = yaml.safe_load(content)
            except ImportError as err:
                raise ImportError(
                    "PyYAML is required for YAML config files. "
                    "Install with: pip install pyyaml"
                ) from err
        else:
            data = json.loads(content)

        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "model": self.model,
            "api_key": self.api_key,
            "provider": self.provider,
            "base_url": self.base_url,
            "context_window": self._context_window,
            "max_tokens": self._max_tokens,
            "memory_dir": self.memory_dir,
            "session_window": self.session_window,
            "sandbox_workspace": self.sandbox_workspace,
            "enable_network": self.enable_network,
            "max_iterations": self.max_iterations,
            "tool_timeout": self.tool_timeout,
            "system_prompt": self.system_prompt,
            "extra_config": self.extra_config,
            "security": self.security.__dict__ if self.security else None,
            "cost_control": self.cost_control.__dict__ if self.cost_control else None,
            "observability": self.observability.__dict__ if self.observability else None,
            "storage": self.storage.__dict__ if self.storage else None,
            "offload": self.offload.__dict__ if self.offload else None,
        }
