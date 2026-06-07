"""
Theme system for Harness Client.

Provides color palettes and stylesheet generation for consistent UI styling.
"""

from harness_client.themes.dark import DarkTheme

# Current active theme
_current_theme = DarkTheme()


def get_theme() -> DarkTheme:
    """Get the current active theme."""
    return _current_theme


def apply_theme(app):
    """Apply the current theme to the application."""
    from harness_client.themes.stylesheet import generate_stylesheet

    stylesheet = generate_stylesheet(_current_theme)
    app.setStyleSheet(stylesheet)