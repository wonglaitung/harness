"""
Settings manager for persisting user configuration.
"""

import json
import logging
import platform
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


def get_config_dir() -> Path:
    """Get unified config directory (~/.harness)."""
    return Path.home() / ".harness"


def get_old_config_dir() -> Path:
    """Get legacy platform-specific config directory for migration."""
    system = platform.system()
    if system == "Windows":
        base = Path.home() / "AppData" / "Local"
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".config"
    return base / "HarnessClient"


def migrate_old_config() -> None:
    """Migrate configuration from old location to new ~/.harness directory."""
    old_dir = get_old_config_dir()
    new_dir = get_config_dir()

    if not old_dir.exists():
        return

    # Create new directory if needed
    new_dir.mkdir(parents=True, exist_ok=True)

    # Migrate settings.json
    old_settings = old_dir / "settings.json"
    new_settings = new_dir / "settings.json"
    if old_settings.exists() and not new_settings.exists():
        logger.info(f"Migrating settings from {old_settings} to {new_settings}")
        shutil.copy2(old_settings, new_settings)

    # Migrate mcp.json
    old_mcp = old_dir / "mcp.json"
    new_mcp = new_dir / "mcp.json"
    if old_mcp.exists() and not new_mcp.exists():
        logger.info(f"Migrating MCP config from {old_mcp} to {new_mcp}")
        shutil.copy2(old_mcp, new_mcp)

    logger.info(f"Configuration migrated to {new_dir}")


@dataclass
class AppSettings:
    """Application settings."""

    provider: str = "anthropic"
    api_key: str = ""
    base_url: str = ""
    model: str = "claude-sonnet-4-6"
    context_window: str = "auto"  # "auto", "32k", "64k", "128k", "200k", or number string
    tool_result_role: str = "tool"  # "tool" (native) or "user" (compatibility mode for proxy APIs)
    temperature: float = 0.3  # Lower = more deterministic, range 0.0-1.0
    auto_save: bool = True
    stream: bool = True
    max_iterations: int = 10  # 业界标准默认值（与 SDK 一致）
    auto_update_memory: bool = True  # Allow agent to autonomously update Core Memory
    work_dir: str = ""
    remember_dir: bool = True
    theme_mode: str = "auto"  # "auto", "light", "dark"
    # Routing settings
    enable_routing: bool = False
    high_model: str = ""
    low_model: str = ""
    router_model_path: str = ""
    router_url: str = ""
    # Browser settings
    browser_type: str = "msedge"  # msedge, chrome, chromium, firefox
    browser_headless: bool = False
    browser_screenshot: bool = True
    browser_timeout: int = 30000  # milliseconds
    # Cost estimation settings (USD per 1M tokens)
    input_cost_per_1m: float = 3.0   # Default: Claude Sonnet 4 pricing
    output_cost_per_1m: float = 15.0  # Default: Claude Sonnet 4 pricing

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AppSettings":
        """Create from dictionary."""
        return cls(
            provider=data.get("provider", "anthropic"),
            api_key=data.get("api_key", ""),
            base_url=data.get("base_url", ""),
            model=data.get("model", "claude-sonnet-4-6"),
            context_window=data.get("context_window", "auto"),
            tool_result_role=data.get("tool_result_role", "tool"),
            temperature=data.get("temperature", 0.3),
            auto_save=data.get("auto_save", True),
            stream=data.get("stream", True),
            max_iterations=data.get("max_iterations", 10),
            auto_update_memory=data.get("auto_update_memory", True),
            work_dir=data.get("work_dir", ""),
            remember_dir=data.get("remember_dir", True),
            theme_mode=data.get("theme_mode", "auto"),
            # Routing settings
            enable_routing=data.get("enable_routing", False),
            high_model=data.get("high_model", ""),
            low_model=data.get("low_model", ""),
            router_model_path=data.get("router_model_path", ""),
            router_url=data.get("router_url", ""),
            # Browser settings
            browser_type=data.get("browser_type", "msedge"),
            browser_headless=data.get("browser_headless", False),
            browser_screenshot=data.get("browser_screenshot", True),
            browser_timeout=data.get("browser_timeout", 30000),
            # Cost estimation settings
            input_cost_per_1m=data.get("input_cost_per_1m", 3.0),
            output_cost_per_1m=data.get("output_cost_per_1m", 15.0),
        )


class SettingsManager:
    """Manages persistent application settings."""

    def __init__(self):
        # Migrate old config before initializing
        migrate_old_config()

        self.config_dir = get_config_dir()
        self.config_file = self.config_dir / "settings.json"
        self._settings: AppSettings | None = None

    def load(self) -> AppSettings:
        """Load settings from disk."""
        if self._settings is not None:
            return self._settings

        # Ensure directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        if self.config_file.exists():
            try:
                data = json.loads(self.config_file.read_text(encoding="utf-8"))
                self._settings = AppSettings.from_dict(data)
            except (json.JSONDecodeError, KeyError):
                self._settings = AppSettings()
        else:
            self._settings = AppSettings()

        return self._settings

    def save(self, settings: AppSettings):
        """Save settings to disk."""
        self._settings = settings

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Write settings
        self.config_file.write_text(
            json.dumps(settings.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def get(self) -> AppSettings:
        """Get current settings (load if needed)."""
        if self._settings is None:
            self._settings = self.load()
        return self._settings

    def update(self, **kwargs):
        """Update specific settings."""
        settings = self.get()
        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
        self.save(settings)
