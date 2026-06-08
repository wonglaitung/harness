"""
Dark theme color palette - inspired by Athlon Agent design.

All colors are defined as hex strings for easy use in QSS and HTML.
"""


class DarkTheme:
    """Dark theme color palette with semantic naming."""

    # Background hierarchy (darkest to lighter)
    APP_BACKGROUND = "#101012"  # Main window background
    CHROME = "#18181B"  # Title bar, sidebar background
    PANEL = "#262628"  # Panel background
    PANEL_ALT = "#2A2A2D"  # Alternate panel background
    COMPOSER = "#2A2A2D"  # Input area background

    # Chat background gradient (top to bottom)
    CHAT_BACKGROUND_TOP = "#141416"
    CHAT_BACKGROUND_BOTTOM = "#101012"

    # Borders
    BORDER = "#3F3F46"
    BORDER_LIGHT = "#505050"

    # Text colors
    TEXT = "#F4F4F5"  # Primary text
    TEXT_SUBTLE = "#A1A1AA"  # Secondary/hint text
    TEXT_DISABLED = "#71717A"  # Disabled state

    # Accent colors (blue)
    ACCENT = "#2563EB"
    ACCENT_HOVER = "#1D4ED8"
    ACCENT_LIGHT = "#93C5FD"  # Light accent for text

    # Status colors
    SUCCESS = "#10B981"
    SUCCESS_HOVER = "#059669"
    DANGER = "#E11D48"
    DANGER_HOVER = "#BE123C"
    WARNING = "#FBBF24"

    # Message bubble colors
    USER_BUBBLE = "#1E3A5F"
    USER_BUBBLE_OPACITY = 0.86
    ASSISTANT_BUBBLE = "#262628"

    # Avatar colors
    AVATAR_ASSISTANT_BG = "#3B3B3B"  # Soft gray for assistant avatar
    AVATAR_USER_BG = "#3B3B3B"  # Soft gray for user avatar (same as assistant)

    # Navigation active state
    NAV_ACTIVE_BG = "#1E3A5F"
    NAV_ACTIVE_TEXT = "#93C5FD"
    NAV_ACTIVE_BORDER = "#3B82F6"  # Bright blue for active indicator

    # Tool call states - Thinking (purple)
    TOOL_THINKING_BORDER = "#6D28D9"
    TOOL_THINKING_BG = "#1E1B2E"
    TOOL_THINKING_TEXT = "#DDD6FE"
    TOOL_THINKING_LIGHT = "#C4B5FD"

    # Tool call states - Success (green)
    TOOL_SUCCESS_BORDER = "#059669"
    TOOL_SUCCESS_BG = "#142A22"
    TOOL_SUCCESS_TEXT = "#6EE7B7"
    TOOL_SUCCESS_LIGHT = "#86EFAC"

    # Tool call states - Failure (red)
    TOOL_FAILURE_BORDER = "#E11D48"
    TOOL_FAILURE_BG = "#2A1418"
    TOOL_FAILURE_TEXT = "#FDA4AF"

    # Hover states (different contexts)
    HOVER_NEUTRAL = "#27272A"  # Neutral hover (gray)
    HOVER_NEUTRAL_ALT = "#2F2F34"  # Alternate neutral
    HOVER_ACTIVE = "#254766"  # Active item hover (blue tint)
    HOVER_TOOL = "#242237"  # Tool card hover (purple tint)
    HOVER_TOOL_PRESSED = "#2C2942"
    HOVER_SURFACE = "#2A2A2D"  # Surface hover
    HOVER_SURFACE_PRESSED = "#33333A"

    # Selection states
    SELECTION_ACTIVE = "#1E3A5F"
    SELECTION_INACTIVE = "#243A55"
    SELECTION_BORDER = "#2F5C8E"

    # Scrollbar
    SCROLL_THUMB = "#9494A8"
    SCROLL_THUMB_OPACITY = 0.55

    # Code/block background
    CODE_BACKGROUND = "#202023"
    CODE_BACKGROUND_ALT = "#27272A"
    CODE_FOREGROUND = "#F1F5F9"
    CODE_BORDER = "#1E293B"
    CODE_HIGHLIGHT_BLUE = "#93C5FD"

    # Table
    TABLE_BORDER = "#52525B"

    # Menu
    MENU_BACKGROUND = "#27272A"
    MENU_HOVER = "#3F3F46"

    # Toast/notification
    TOAST_BACKGROUND = "#0F172A"
    TOAST_BORDER = "#334155"

    # Icon badge gradient
    ICON_BADGE_START = "#E0F2FE"
    ICON_BADGE_END = "#0284C7"

    # @ completion badges
    AT_SKILL_BADGE_BG = "#1E1B2E"
    AT_SKILL_BADGE_BORDER = "#6D28D9"
    AT_SKILL_BADGE_TEXT = "#DDD6FE"
    AT_FILE_BADGE_BG = "#2A2A2D"
    AT_FILE_BADGE_BORDER = "#3F3F46"
    AT_FILE_BADGE_TEXT = "#A1A1AA"

    # Disabled state
    DISABLED_BACKGROUND = "#3F3F46"