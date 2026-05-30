"""
Settings manager for persisting user configuration.
"""

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict
import platform


def get_config_dir() -> Path:
    """Get platform-specific config directory."""
    system = platform.system()
    if system == "Windows":
        # Use AppData/Local on Windows
        base = Path.home() / "AppData" / "Local"
    elif system == "Darwin":
        # Use ~/Library/Application Support on macOS
        base = Path.home() / "Library" / "Application Support"
    else:
        # Use XDG config on Linux
        base = Path.home() / ".config"
    return base / "HarnessClient"


@dataclass
class AppSettings:
    """Application settings."""
    provider: str = "anthropic"
    api_key: str = ""
    base_url: str = ""
    model: str = "claude-sonnet-4-6"
    auto_save: bool = True
    stream: bool = True
    max_iterations: int = 20
    work_dir: str = ""
    remember_dir: bool = True

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
            auto_save=data.get("auto_save", True),
            stream=data.get("stream", True),
            max_iterations=data.get("max_iterations", 20),
            work_dir=data.get("work_dir", ""),
            remember_dir=data.get("remember_dir", True),
        )


class SettingsManager:
    """Manages persistent application settings."""

    def __init__(self):
        self.config_dir = get_config_dir()
        self.config_file = self.config_dir / "settings.json"
        self._settings: Optional[AppSettings] = None

    def load(self) -> AppSettings:
        """Load settings from disk."""
        if self._settings is not None:
            return self._settings

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
            json.dumps(settings.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8"
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
