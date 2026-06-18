"""
Theme-aware widget mixin for Harness Client.

Provides a base class that automatically re-applies component styles
when the theme changes, ensuring all UI elements stay in sync.
"""

from PyQt6.QtWidgets import QWidget

from harness_client.themes import register_theme_listener, unregister_theme_listener, get_theme


class ThemeAwareWidget(QWidget):
    """
    Base widget that automatically updates when theme changes.

    Subclasses should implement ``_apply_theme_style()`` which contains
    all QSS / color logic. The method is called on construction and
    every time the theme switches.
    """

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._theme_style_applied = False
        self._apply_theme_style()
        self._theme_style_applied = True
        register_theme_listener(self._on_theme_changed)

    def __del__(self):
        try:
            unregister_theme_listener(self._on_theme_changed)
        except Exception:
            pass

    def _on_theme_changed(self) -> None:
        """Called automatically when the theme changes."""
        if not self._theme_style_applied:
            return
        self._apply_theme_style()

    def _apply_theme_style(self) -> None:
        """
        Apply theme-dependent styles to this widget and its children.

        Override this method in subclasses to customize appearance.
        The default implementation does nothing.
        """
        pass

    def theme(self):
        """Convenience access to the current theme palette."""
        return get_theme()
