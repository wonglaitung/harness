"""
Banking-grade dark theme color palette.

Designed for trust, professionalism, and clarity in financial contexts.
Moves away from "AI Blue" toward a deeper "Trust Blue" aesthetic.

All colors are defined as hex strings for easy use in QSS and HTML.
"""


class DarkTheme:
    """Banking-grade dark theme with semantic naming."""

    # === Background Hierarchy ===
    # More depth and contrast than typical dark themes
    APP_BACKGROUND = "#0D1117"  # Main window - deepest
    CHROME = "#161B22"  # Title bar, sidebar
    PANEL = "#21262D"  # Panel background
    PANEL_ALT = "#292E36"  # Alternate panel
    COMPOSER = "#1C2128"  # Input area

    # Chat background gradient
    CHAT_BACKGROUND_TOP = "#0F1419"
    CHAT_BACKGROUND_BOTTOM = "#0D1117"

    # === Border System ===
    BORDER = "#30363D"  # Primary border
    BORDER_LIGHT = "#444C56"  # Hover/lighter border
    BORDER_FOCUS = "#58A6FF"  # Focus ring

    # === Text Colors ===
    TEXT = "#E6EDF3"  # Primary text
    TEXT_SUBTLE = "#8B949E"  # Secondary text
    TEXT_MUTED = "#6E7681"  # Muted/disabled hint
    TEXT_DISABLED = "#484F58"  # Disabled state

    # === Trust Blue (Not AI Blue) ===
    # Deeper, more authoritative blue for financial trust
    ACCENT = "#1F6FEB"  # Trust blue - primary accent
    ACCENT_HOVER = "#388BFD"  # Hover state
    ACCENT_LIGHT = "#58A6FF"  # Light accent for highlights
    ACCENT_SUBTLE = "#1C3A5E"  # Subtle accent background

    # === Semantic Colors ===
    # Success (green)
    SUCCESS = "#2EA043"
    SUCCESS_HOVER = "#3FB950"
    SUCCESS_BG = "#1A2F23"
    SUCCESS_TEXT = "#6EE7B7"

    # Warning (amber)
    WARNING = "#D29922"
    WARNING_HOVER = "#E3B341"
    WARNING_BG = "#2E2518"
    WARNING_TEXT = "#F0C674"

    # Danger (red)
    DANGER = "#DA3633"
    DANGER_HOVER = "#F85149"
    DANGER_BG = "#3D1F20"
    DANGER_TEXT = "#FDA4AF"

    # Info (blue)
    INFO = "#58A6FF"
    INFO_BG = "#1C2B3E"
    INFO_TEXT = "#93C5FD"

    # === Message Bubbles ===
    USER_BUBBLE = "#1C3A5E"  # Trust blue user message
    USER_BUBBLE_OPACITY = 1.0
    ASSISTANT_BUBBLE = "#21262D"  # Neutral assistant message

    # === Avatar Colors ===
    AVATAR_ASSISTANT_BG = "#444C56"

    # === Navigation ===
    NAV_ACTIVE_BG = "#1C3A5E"
    NAV_ACTIVE_TEXT = "#58A6FF"
    NAV_ACTIVE_BORDER = "#1F6FEB"

    # === Tool Call States ===
    # Thinking (neutral)
    TOOL_THINKING_BORDER = "#6E7681"
    TOOL_THINKING_BG = "#161B22"
    TOOL_THINKING_TEXT = "#8B949E"
    TOOL_THINKING_LIGHT = "#A5A5A5"

    # Success (green)
    TOOL_SUCCESS_BORDER = "#2EA043"
    TOOL_SUCCESS_BG = "#1A2F23"
    TOOL_SUCCESS_TEXT = "#6EE7B7"
    TOOL_SUCCESS_LIGHT = "#86EFAC"

    # Failure (red)
    TOOL_FAILURE_BORDER = "#DA3633"
    TOOL_FAILURE_BG = "#3D1F20"
    TOOL_FAILURE_TEXT = "#FDA4AF"

    # === Hover States ===
    HOVER_NEUTRAL = "#21262D"
    HOVER_NEUTRAL_ALT = "#292E36"
    HOVER_ACTIVE = "#1C3A5E"
    HOVER_TOOL = "#1C2128"
    HOVER_TOOL_PRESSED = "#292E36"
    HOVER_SURFACE = "#292E36"
    HOVER_SURFACE_PRESSED = "#30363D"

    # === Selection States ===
    SELECTION_ACTIVE = "#1C3A5E"
    SELECTION_INACTIVE = "#21262D"
    SELECTION_BORDER = "#388BFD"

    # === Scrollbar ===
    SCROLL_THUMB = "#6E7681"
    SCROLL_THUMB_OPACITY = 0.55

    # === Code Blocks ===
    CODE_BACKGROUND = "#161B22"
    CODE_BACKGROUND_ALT = "#1C2128"
    CODE_FOREGROUND = "#E6EDF3"
    CODE_BORDER = "#30363D"
    CODE_HIGHLIGHT_BLUE = "#58A6FF"

    # === Table ===
    TABLE_BORDER = "#444C56"

    # === Menu ===
    MENU_BACKGROUND = "#21262D"
    MENU_HOVER = "#30363D"

    # === Toast/Notification ===
    TOAST_BACKGROUND = "#161B22"
    TOAST_BORDER = "#30363D"

    # === Icon Badges ===
    ICON_BADGE_START = "#E0F2FE"
    ICON_BADGE_END = "#1F6FEB"

    # === @ Completion Badges ===
    AT_SKILL_BADGE_BG = "#2E2518"
    AT_SKILL_BADGE_BORDER = "#D29922"
    AT_SKILL_BADGE_TEXT = "#F0C674"
    AT_FILE_BADGE_BG = "#21262D"
    AT_FILE_BADGE_BORDER = "#30363D"
    AT_FILE_BADGE_TEXT = "#8B949E"

    # === Disabled State ===
    DISABLED_BACKGROUND = "#30363D"

    # === Shape System (Banking prefers sharper edges) ===
    RADIUS_SM = "3px"  # Small: tags, mini buttons
    RADIUS_MD = "6px"  # Standard: buttons, inputs, panels
    RADIUS_LG = "8px"  # Large: message bubbles, cards

    # === MCP Server Buttons ===
    MCP_CONNECT_BG = "#1C3A5E"
    MCP_CONNECT_BG_HOVER = "#254766"
    MCP_CONNECT_TEXT = "#58A6FF"
    MCP_DISCONNECT_BG = "#3D1F20"
    MCP_DISCONNECT_BG_HOVER = "#4D2F30"
    MCP_DISCONNECT_TEXT = "#FDA4AF"

    # === Status Indicators ===
    STATUS_CONNECTED = "#2EA043"
    STATUS_CONNECTING = "#D29922"
    STATUS_ERROR = "#DA3633"
    STATUS_DISCONNECTED = "#6E7681"
