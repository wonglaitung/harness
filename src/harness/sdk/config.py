"""Configuration classes for Harness SDK."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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
    provider: str = "anthropic"  # "anthropic", "openai", or "custom"
    base_url: str | None = None  # For custom endpoints (e.g., local LLM, Azure)
    max_tokens: int = 4096
    temperature: float = 1.0

    # Memory settings
    memory_dir: str = ".harness/memory"
    session_window: int = 50

    # Tool settings
    sandbox_workspace: str | None = None
    enable_network: bool = False

    # Loop settings
    max_iterations: int = 100
    tool_timeout: float = 30.0

    # Optional settings
    system_prompt: str = ""
    extra_config: dict[str, Any] = field(default_factory=dict)

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
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "memory_dir": self.memory_dir,
            "session_window": self.session_window,
            "sandbox_workspace": self.sandbox_workspace,
            "enable_network": self.enable_network,
            "max_iterations": self.max_iterations,
            "tool_timeout": self.tool_timeout,
            "system_prompt": self.system_prompt,
            "extra_config": self.extra_config,
        }
