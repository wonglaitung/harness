"""Configuration classes for Harness SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from harness.model_presets import get_default_output_tokens, get_model_preset, parse_context_window


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
    system_prompt: str = ""
    extra_config: dict[str, Any] = field(default_factory=dict)

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
        }
