"""
Progress formatters for displaying agent execution progress.

Provides utilities to format and display progress events in different styles.
"""

from harness.types import ProgressEvent, ProgressEventType


class ProgressFormatter:
    """Formatter for progress events."""

    @staticmethod
    def simple(event: ProgressEvent) -> str:
        """
        Simple format: just event type and message.

        Example: [tool_call] Executing: read
        """
        return f"[{event.type.value}] {event.message}"

    @staticmethod
    def detailed(event: ProgressEvent) -> str:
        """
        Detailed format with timestamp and data.

        Example: [14:32:01] tool_call: Executing: read | {"tool": "read"}
        """
        ts = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        duration = f" ({event.duration_ms:.0f}ms)" if event.duration_ms else ""

        # For LLM response, include content preview or tool calls
        if event.type == ProgressEventType.LLM_RESPONSE:
            content = event.data.get("content", "")
            has_tool_calls = event.data.get("has_tool_calls", False)
            tool_names = event.data.get("tool_names", [])

            # Remove content from data dict for display
            display_data = {
                k: v
                for k, v in event.data.items()
                if k not in ("content", "has_tool_calls", "tool_names")
            }
            data_str = f" | {display_data}" if display_data else ""

            base = f"[{ts}] {event.type.value}: {event.message}{duration}{data_str}"

            # Show content if present (truncated to 20 chars)
            if content and content.strip():
                content_preview = content[:20] + "..." if len(content) > 20 else content
                return f"{base}\n    Content: {content_preview}"
            # Or show tool calls if any
            elif has_tool_calls and tool_names:
                return f"{base}\n    Tools: {', '.join(tool_names)}"
            return base

        data_str = f" | {event.data}" if event.data else ""
        return f"[{ts}] {event.type.value}: {event.message}{duration}{data_str}"

    @staticmethod
    def colored(event: ProgressEvent) -> str:
        """
        Colored format with ANSI colors for terminal.

        Requires terminal with ANSI color support.
        """
        colors = {
            ProgressEventType.LOOP_START: "\033[92m",  # Green
            ProgressEventType.LOOP_END: "\033[92m",  # Green
            ProgressEventType.STATE_CHANGE: "\033[94m",  # Blue
            ProgressEventType.TOOL_CALL: "\033[93m",  # Yellow
            ProgressEventType.TOOL_RESULT: "\033[93m",  # Yellow
            ProgressEventType.LLM_CALL: "\033[95m",  # Magenta
            ProgressEventType.LLM_RESPONSE: "\033[95m",  # Magenta
            ProgressEventType.ITERATION: "\033[90m",  # Gray
            ProgressEventType.ERROR: "\033[91m",  # Red
        }
        reset = "\033[0m"
        color = colors.get(event.type, "")
        ts = event.timestamp.strftime("%H:%M:%S")
        duration = f" ({event.duration_ms:.0f}ms)" if event.duration_ms else ""

        # For LLM response, include content preview or tool calls
        if event.type == ProgressEventType.LLM_RESPONSE:
            content = event.data.get("content", "")
            has_tool_calls = event.data.get("has_tool_calls", False)
            tool_names = event.data.get("tool_names", [])

            base = f"[{ts}] {color}{event.message}{reset}{duration}"

            # Show content if present (truncated to 20 chars, single line)
            if content and content.strip():
                content_preview = content[:20] + "..." if len(content) > 20 else content
                return f"{base} {content_preview}"
            # Or show tool calls if any
            elif has_tool_calls and tool_names:
                return f"{base} 📎 {', '.join(tool_names)}"
            return base

        return f"[{ts}] {color}{event.message}{reset}{duration}"

    @staticmethod
    def emoji(event: ProgressEvent) -> str:
        """
        Format with emoji icons for different event types.

        Example: [14:32:01] 🔧 Executing: read
        """
        icons = {
            ProgressEventType.LOOP_START: "🚀",
            ProgressEventType.LOOP_END: "✅",
            ProgressEventType.STATE_CHANGE: "📍",
            ProgressEventType.TOOL_CALL: "🔧",
            ProgressEventType.TOOL_RESULT: "⚙️",
            ProgressEventType.LLM_CALL: "🤖",
            ProgressEventType.LLM_RESPONSE: "💬",
            ProgressEventType.ITERATION: "🔄",
            ProgressEventType.ERROR: "❌",
        }
        icon = icons.get(event.type, "•")
        ts = event.timestamp.strftime("%H:%M:%S")
        duration = f" ({event.duration_ms:.0f}ms)" if event.duration_ms else ""

        # For LLM response, include content preview or tool calls
        if event.type == ProgressEventType.LLM_RESPONSE:
            content = event.data.get("content", "")
            has_tool_calls = event.data.get("has_tool_calls", False)
            tool_names = event.data.get("tool_names", [])

            base = f"[{ts}] {icon} {event.message}{duration}"

            # Show content if present (truncated to 20 chars, single line)
            if content and content.strip():
                content_preview = content[:20] + "..." if len(content) > 20 else content
                return f"{base} {content_preview}"
            # Or show tool calls if any
            elif has_tool_calls and tool_names:
                return f"{base} 📎 {', '.join(tool_names)}"
            return base

        return f"[{ts}] {icon} {event.message}{duration}"


def create_progress_handler(
    format_style: str = "emoji",
    quiet: bool = False,
) -> callable:
    """
    Create a progress handler with specified format.

    Args:
        format_style: One of "simple", "detailed", "colored", "emoji"
        quiet: If True, suppress output (returns no-op handler)

    Returns:
        A progress callback function

    Example:
        >>> handler = create_progress_handler("colored")
        >>> result = await agent.run("task", on_progress=handler)
    """
    if quiet:
        return lambda event: None

    formatters = {
        "simple": ProgressFormatter.simple,
        "detailed": ProgressFormatter.detailed,
        "colored": ProgressFormatter.colored,
        "emoji": ProgressFormatter.emoji,
    }

    formatter = formatters.get(format_style, ProgressFormatter.emoji)

    def handler(event: ProgressEvent) -> None:
        print(formatter(event))

    return handler
