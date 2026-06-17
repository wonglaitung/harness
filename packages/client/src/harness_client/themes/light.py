"""
Banking-grade light theme color palette.

Designed for trust, professionalism, and clarity in financial contexts.
Optimized for daylight environments and high contrast readability.

All colors are defined as hex strings for easy use in QSS and HTML.
"""


class LightTheme:
    """Banking-grade light theme with semantic naming."""

    # === Background Hierarchy ===
    # Light to dark progression for clear visual hierarchy
    APP_BACKGROUND = "#FFFFFF"  # Main window - pure white
    CHROME = "#F8FAFC"  # Title bar, sidebar (slate-50)
    PANEL = "#F1F5F9"  # Panel background (slate-100)
    PANEL_ALT = "#E2E8F0"  # Alternate panel (slate-200)
    COMPOSER = "#FFFFFF"  # Input area - clean white for focus

    # Chat background (flat white, no gradient needed)
    CHAT_BACKGROUND_TOP = "#FFFFFF"
    CHAT_BACKGROUND_BOTTOM = "#F8FAFC"

    # === Border System ===
    BORDER = "#CBD5E1"  # Primary border (slate-300)
    BORDER_LIGHT = "#94A3B8"  # Hover/lighter border (slate-400)
    BORDER_FOCUS = "#1F6FEB"  # Focus ring (Trust Blue)

    # === Text Colors ===
    # Using slate-800 instead of pure black for softer appearance
    TEXT = "#1E293B"  # Primary text (slate-800)
    TEXT_SUBTLE = "#64748B"  # Secondary text (slate-500)
    TEXT_MUTED = "#94A3B8"  # Muted/disabled hint (slate-400)
    TEXT_DISABLED = "#CBD5E1"  # Disabled state (slate-300)

    # === Trust Blue (Same core identity as dark theme) ===
    # Adjusted hover/active states for light background visibility
    ACCENT = "#1F6FEB"  # Trust blue - primary accent
    ACCENT_HOVER = "#1A4A9E"  # Hover state - darker for contrast
    ACCENT_LIGHT = "#388BFD"  # Light accent for highlights
    ACCENT_SUBTLE = "#E0F2FE"  # Subtle accent background (sky-100)

    # === Semantic Colors ===
    # Success (green)
    SUCCESS = "#16A34A"  # Green-600
    SUCCESS_HOVER = "#15803D"  # Green-700
    SUCCESS_BG = "#F0FDF4"  # Green-50
    SUCCESS_TEXT = "#166534"  # Green-800

    # Warning (amber)
    WARNING = "#CA8A04"  # Yellow-600
    WARNING_HOVER = "#A16207"  # Yellow-700
    WARNING_BG = "#FEFCE8"  # Yellow-50
    WARNING_TEXT = "#854D0E"  # Yellow-800

    # Danger (red)
    DANGER = "#DC2626"  # Red-600
    DANGER_HOVER = "#B91C1C"  # Red-700
    DANGER_BG = "#FEF2F2"  # Red-50
    DANGER_TEXT = "#991B1B"  # Red-800

    # Info (blue)
    INFO = "#2563EB"  # Blue-600
    INFO_BG = "#EFF6FF"  # Blue-50
    INFO_TEXT = "#1E40AF"  # Blue-800

    # === Message Bubbles ===
    USER_BUBBLE = "#E0F2FE"  # Trust blue tint (sky-100)
    USER_BUBBLE_OPACITY = 1.0
    ASSISTANT_BUBBLE = "#F1F5F9"  # Neutral gray (slate-100)

    # === Avatar Colors ===
    AVATAR_ASSISTANT_BG = "#CBD5E1"  # slate-300

    # === Navigation ===
    NAV_ACTIVE_BG = "#E0F2FE"  # sky-100
    NAV_ACTIVE_TEXT = "#1F6FEB"  # Trust Blue
    NAV_ACTIVE_BORDER = "#388BFD"  # Light accent

    # === Tool Call States ===
    # Thinking (neutral)
    TOOL_THINKING_BORDER = "#94A3B8"  # slate-400
    TOOL_THINKING_BG = "#F8FAFC"  # slate-50
    TOOL_THINKING_TEXT = "#64748B"  # slate-500
    TOOL_THINKING_LIGHT = "#64748B"

    # Success (green)
    TOOL_SUCCESS_BORDER = "#16A34A"  # Green-600
    TOOL_SUCCESS_BG = "#F0FDF4"  # Green-50
    TOOL_SUCCESS_TEXT = "#166534"  # Green-800
    TOOL_SUCCESS_LIGHT = "#22C55E"  # Green-500

    # Failure (red)
    TOOL_FAILURE_BORDER = "#DC2626"  # Red-600
    TOOL_FAILURE_BG = "#FEF2F2"  # Red-50
    TOOL_FAILURE_TEXT = "#991B1B"  # Red-800

    # === Hover States ===
    HOVER_NEUTRAL = "#F1F5F9"  # slate-100
    HOVER_NEUTRAL_ALT = "#E2E8F0"  # slate-200
    HOVER_ACTIVE = "#E0F2FE"  # sky-100
    HOVER_TOOL = "#F8FAFC"  # slate-50
    HOVER_TOOL_PRESSED = "#E2E8F0"  # slate-200
    HOVER_SURFACE = "#E2E8F0"  # slate-200
    HOVER_SURFACE_PRESSED = "#CBD5E1"  # slate-300

    # === Selection States ===
    SELECTION_ACTIVE = "#E0F2FE"  # sky-100
    SELECTION_INACTIVE = "#F1F5F9"  # slate-100
    SELECTION_BORDER = "#388BFD"  # Light accent

    # === Scrollbar ===
    SCROLL_THUMB = "#94A3B8"  # slate-400
    SCROLL_THUMB_OPACITY = 0.75

    # === Code Blocks ===
    CODE_BACKGROUND = "#F8FAFC"  # slate-50
    CODE_BACKGROUND_ALT = "#F1F5F9"  # slate-100
    CODE_FOREGROUND = "#1E293B"  # slate-800
    CODE_BORDER = "#CBD5E1"  # slate-300
    CODE_HIGHLIGHT_BLUE = "#2563EB"  # Blue-600

    # === Table ===
    TABLE_BORDER = "#CBD5E1"  # slate-300

    # === Menu ===
    MENU_BACKGROUND = "#FFFFFF"
    MENU_HOVER = "#F1F5F9"  # slate-100

    # === Toast/Notification ===
    TOAST_BACKGROUND = "#FFFFFF"
    TOAST_BORDER = "#CBD5E1"  # slate-300

    # === Icon Badges ===
    ICON_BADGE_START = "#EFF6FF"  # Blue-50
    ICON_BADGE_END = "#2563EB"  # Blue-600

    # === @ Completion Badges ===
    AT_SKILL_BADGE_BG = "#FEFCE8"  # Yellow-50
    AT_SKILL_BADGE_BORDER = "#CA8A04"  # Yellow-600
    AT_SKILL_BADGE_TEXT = "#854D0E"  # Yellow-800
    AT_FILE_BADGE_BG = "#F1F5F9"  # slate-100
    AT_FILE_BADGE_BORDER = "#CBD5E1"  # slate-300
    AT_FILE_BADGE_TEXT = "#64748B"  # slate-500

    # === Disabled State ===
    DISABLED_BACKGROUND = "#E2E8F0"  # slate-200

    # === Shape System (Banking prefers sharper edges) ===
    RADIUS_SM = "3px"  # Small: tags, mini buttons
    RADIUS_MD = "6px"  # Standard: buttons, inputs, panels
    RADIUS_LG = "8px"  # Large: message bubbles, cards

    # === MCP Server Buttons ===
    MCP_CONNECT_BG = "#E0F2FE"  # sky-100
    MCP_CONNECT_BG_HOVER = "#BAE6FD"  # sky-200
    MCP_CONNECT_TEXT = "#1F6FEB"  # Trust Blue
    MCP_DISCONNECT_BG = "#FEF2F2"  # Red-50
    MCP_DISCONNECT_BG_HOVER = "#FEE2E2"  # Red-100
    MCP_DISCONNECT_TEXT = "#DC2626"  # Red-600

    # === Status Indicators ===
    STATUS_CONNECTED = "#16A34A"  # Green-600
    STATUS_CONNECTING = "#CA8A04"  # Yellow-600
    STATUS_ERROR = "#DC2626"  # Red-600
    STATUS_DISCONNECTED = "#94A3B8"  # slate-400

    # ============================================================
    # Typography System (Same as dark theme)
    # ============================================================
    FONT_FAMILY = '"Segoe UI", "Microsoft YaHei UI", system-ui, sans-serif'
    FONT_FAMILY_MONO = '"Consolas", "Courier New", monospace'

    # Font sizes (in px for QSS, pt for rich text)
    FONT_SIZE_XS = "11px"
    FONT_SIZE_SM = "12px"
    FONT_SIZE_BASE = "13px"
    FONT_SIZE_MD = "14px"
    FONT_SIZE_LG = "16px"
    FONT_SIZE_XL = "18px"
    FONT_SIZE_2XL = "24px"

    # Font sizes for rich text (pt)
    FONT_SIZE_PT_XS = 9
    FONT_SIZE_PT_SM = 10
    FONT_SIZE_PT_BASE = 11
    FONT_SIZE_PT_MD = 12
    FONT_SIZE_PT_LG = 14
    FONT_SIZE_PT_XL = 16

    # Line heights (multiplier)
    LINE_HEIGHT_TIGHT = 1.25
    LINE_HEIGHT_NORMAL = 1.5
    LINE_HEIGHT_RELAXED = 1.75

    # Font weights
    FONT_WEIGHT_NORMAL = "normal"
    FONT_WEIGHT_MEDIUM = "500"
    FONT_WEIGHT_BOLD = "bold"
    FONT_WEIGHT_SEMIBOLD = "600"