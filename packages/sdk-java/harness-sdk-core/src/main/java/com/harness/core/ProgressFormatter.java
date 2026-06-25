package com.harness.core;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Map;

import com.harness.types.ProgressEvent;
import com.harness.types.ProgressEventType;

/**
 * Progress formatters for displaying agent execution progress.
 *
 * Provides utilities to format and display progress events in different styles.
 *
 * Example:
 * <pre>
 * ProgressEvent event = new ProgressEvent(ProgressEventType.TOOL_CALL, "Executing: read");
 *
 * // Different format styles
 * String simple = ProgressFormatter.simple(event);
 * String detailed = ProgressFormatter.detailed(event);
 * String colored = ProgressFormatter.colored(event);
 * String emoji = ProgressFormatter.emoji(event);
 * </pre>
 */
public class ProgressFormatter {

    private static final DateTimeFormatter TIME_FORMAT = DateTimeFormatter.ofPattern("HH:mm:ss");
    private static final DateTimeFormatter DETAILED_TIME_FORMAT = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    // ANSI color codes
    private static final String RESET = "\u001B[0m";
    private static final String GREEN = "\u001B[92m";
    private static final String BLUE = "\u001B[94m";
    private static final String YELLOW = "\u001B[93m";
    private static final String MAGENTA = "\u001B[95m";
    private static final String GRAY = "\u001B[90m";
    private static final String RED = "\u001B[91m";

    /**
     * Simple format: just event type and message.
     */
    public static String simple(ProgressEvent event) {
        return String.format("[%s] %s", event.type().getValue(), event.message());
    }

    /**
     * Detailed format with timestamp and data.
     */
    public static String detailed(ProgressEvent event) {
        String ts = event.timestamp().format(DETAILED_TIME_FORMAT);
        String duration = event.durationMs() != null ? String.format(" (%.0fms)", event.durationMs()) : "";

        StringBuilder sb = new StringBuilder();
        sb.append(String.format("[%s] %s: %s%s", ts, event.type().getValue(), event.message(), duration));

        // Add data if present
        Map<String, Object> data = event.data();
        if (data != null && !data.isEmpty()) {
            // Remove large content for display
            Map<String, Object> displayData = new java.util.HashMap<>(data);
            displayData.remove("content");
            displayData.remove("has_tool_calls");
            displayData.remove("tool_names");

            if (!displayData.isEmpty()) {
                sb.append(" | ").append(displayData);
            }

            // Show content preview or tool calls
            String content = (String) data.get("content");
            Boolean hasToolCalls = (Boolean) data.get("has_tool_calls");

            if (content != null && !content.isBlank()) {
                String preview = content.length() > 20 ? content.substring(0, 20) + "..." : content;
                sb.append("\n    Content: ").append(preview);
            } else if (Boolean.TRUE.equals(hasToolCalls)) {
                Object toolNames = data.get("tool_names");
                if (toolNames != null) {
                    sb.append("\n    Tools: ").append(toolNames);
                }
            }
        }

        return sb.toString();
    }

    /**
     * Colored format with ANSI colors for terminal.
     */
    public static String colored(ProgressEvent event) {
        String color = getColorForType(event.type());
        String ts = event.timestamp().format(TIME_FORMAT);
        String duration = event.durationMs() != null ? String.format(" (%.0fms)", event.durationMs()) : "";

        StringBuilder sb = new StringBuilder();
        sb.append(String.format("[%s] %s%s%s", ts, color, event.message(), RESET));

        if (event.durationMs() != null) {
            sb.append(duration);
        }

        // Add data preview
        Map<String, Object> data = event.data();
        if (data != null) {
            String content = (String) data.get("content");
            Boolean hasToolCalls = (Boolean) data.get("has_tool_calls");

            if (content != null && !content.isBlank()) {
                String preview = content.length() > 20 ? content.substring(0, 20) + "..." : content;
                sb.append(" ").append(preview);
            } else if (Boolean.TRUE.equals(hasToolCalls)) {
                Object toolNames = data.get("tool_names");
                if (toolNames != null) {
                    sb.append(" \uD83D\uDCE7 ").append(toolNames); // 📧 emoji
                }
            }
        }

        return sb.toString();
    }

    /**
     * Format with emoji icons for different event types.
     */
    public static String emoji(ProgressEvent event) {
        String icon = getIconForType(event.type());
        String ts = event.timestamp().format(TIME_FORMAT);
        String duration = event.durationMs() != null ? String.format(" (%.0fms)", event.durationMs()) : "";

        StringBuilder sb = new StringBuilder();
        sb.append(String.format("[%s] %s %s", ts, icon, event.message()));

        if (event.durationMs() != null) {
            sb.append(duration);
        }

        // Add data preview
        Map<String, Object> data = event.data();
        if (data != null) {
            String content = (String) data.get("content");
            Boolean hasToolCalls = (Boolean) data.get("has_tool_calls");

            if (content != null && !content.isBlank()) {
                String preview = content.length() > 20 ? content.substring(0, 20) + "..." : content;
                sb.append(" ").append(preview);
            } else if (Boolean.TRUE.equals(hasToolCalls)) {
                Object toolNames = data.get("tool_names");
                if (toolNames != null) {
                    sb.append(" \uD83D\uDCE7 ").append(toolNames);
                }
            }
        }

        return sb.toString();
    }

    private static String getColorForType(ProgressEventType type) {
        return switch (type) {
            case LOOP_START, LOOP_END -> GREEN;
            case STATE_CHANGE -> BLUE;
            case TOOL_CALL, TOOL_RESULT -> YELLOW;
            case LLM_CALL, LLM_RESPONSE -> MAGENTA;
            case ITERATION -> GRAY;
            case ERROR -> RED;
            default -> "";
        };
    }

    private static String getIconForType(ProgressEventType type) {
        return switch (type) {
            case LOOP_START -> "\uD83D\uDE80"; // 🚀
            case LOOP_END -> "✅";
            case STATE_CHANGE -> "\uD83D\uDCCD"; // 📍
            case TOOL_CALL -> "\uD83D\uDD27"; // 🔧
            case TOOL_RESULT -> "⚙\uFE0F";
            case LLM_CALL -> "\uD83E\uDD16"; // 🤖
            case LLM_RESPONSE -> "\uD83D\uDCAC"; // 💬
            case ITERATION -> "\uD83D\uDD04"; // 🔄
            case ERROR -> "❌";
            case TEXT_CHUNK -> "\uD83D\uDCDD"; // 📝
            case STUCK_DETECTED -> "\uD83D\uDD12"; // 🔒
            case ROUTER_DECISION -> "\uD83D\uDD17"; // 🔀
            default -> "•";
        };
    }

    /**
     * Create a progress handler with specified format.
     *
     * @param formatStyle One of "simple", "detailed", "colored", "emoji"
     * @return A progress callback function
     */
    public static java.util.function.Consumer<ProgressEvent> createHandler(String formatStyle) {
        return createHandler(formatStyle, false);
    }

    /**
     * Create a progress handler with specified format.
     *
     * @param formatStyle One of "simple", "detailed", "colored", "emoji"
     * @param quiet If true, suppress output
     * @return A progress callback function
     */
    public static java.util.function.Consumer<ProgressEvent> createHandler(String formatStyle, boolean quiet) {
        if (quiet) {
            return event -> {};
        }

        return switch (formatStyle.toLowerCase()) {
            case "simple" -> event -> System.out.println(simple(event));
            case "detailed" -> event -> System.out.println(detailed(event));
            case "colored" -> event -> System.out.println(colored(event));
            default -> event -> System.out.println(emoji(event));
        };
    }
}
