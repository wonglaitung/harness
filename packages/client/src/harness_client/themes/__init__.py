"""
Theme system for Harness Client.

Provides color palettes and stylesheet generation for consistent UI styling.
Supports both light and dark themes with automatic system detection.
"""

from enum import Enum
from typing import Callable, Union

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QGuiApplication

from harness_client.themes.dark import DarkTheme
from harness_client.themes.light import LightTheme


class ThemeMode(str, Enum):
    """Theme mode selection."""

    AUTO = "auto"  # Follow system preference
    LIGHT = "light"  # Force light theme
    DARK = "dark"  # Force dark theme


# Type alias for theme instances
Theme = Union[LightTheme, DarkTheme]

# Current theme mode (default: auto)
_current_mode = ThemeMode.AUTO

# Current active theme instance
_current_theme: Theme = DarkTheme()

# Application reference for theme updates
_app = None

# Theme change listeners
_listeners: list[Callable] = []


def get_system_theme() -> str:
    """Detect system color scheme preference."""
    try:
        hints = QGuiApplication.styleHints()
        if hints:
            color_scheme = hints.colorScheme()
            if color_scheme == Qt.ColorScheme.Light:
                return "light"
            elif color_scheme == Qt.ColorScheme.Dark:
                return "dark"
    except Exception:
        pass
    return "dark"  # Default to dark if detection fails


def get_theme() -> Theme:
    """Get the current active theme."""
    return _current_theme


def register_theme_listener(callback: Callable) -> None:
    """Register a callback to be notified when the theme changes.

    Args:
        callback: Callable that takes no arguments, invoked on theme change
    """
    _listeners.append(callback)


def unregister_theme_listener(callback: Callable) -> None:
    """Remove a previously registered theme change listener.

    Args:
        callback: The callback to remove
    """
    if callback in _listeners:
        _listeners.remove(callback)


def set_theme_mode(mode: str | ThemeMode, app=None) -> None:
    """
    Set the theme mode and apply it.

    Args:
        mode: "auto", "light", or "dark"
        app: QApplication instance (optional, stored for future updates)
    """
    global _current_mode, _current_theme, _app

    if app:
        _app = app

    # Normalize mode
    if isinstance(mode, str):
        mode = ThemeMode(mode)

    _current_mode = mode

    # Determine actual theme based on mode
    if mode == ThemeMode.AUTO:
        system = get_system_theme()
        _current_theme = LightTheme() if system == "light" else DarkTheme()
    elif mode == ThemeMode.LIGHT:
        _current_theme = LightTheme()
    else:
        _current_theme = DarkTheme()

    # Apply to app if available
    if _app:
        apply_theme(_app)

    # Notify all listeners of theme change
    _notify_theme_changed()


def get_theme_mode() -> ThemeMode:
    """Get the current theme mode setting."""
    return _current_mode


def _notify_theme_changed() -> None:
    """Notify all registered listeners that the theme changed."""
    for callback in _listeners:
        try:
            callback()
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Theme listener error: {e}")


def apply_theme(app) -> None:
    """Apply the current theme to the application."""
    from harness_client.themes.stylesheet import generate_stylesheet

    global _app
    _app = app

    stylesheet = generate_stylesheet(_current_theme)
    app.setStyleSheet(stylesheet)