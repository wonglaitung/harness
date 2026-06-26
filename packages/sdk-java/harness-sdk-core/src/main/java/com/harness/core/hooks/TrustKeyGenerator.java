package com.harness.core.hooks;

import java.util.Map;

/**
 * Utility for generating trust cache keys for tool calls.
 *
 * The trust key is used to cache user's "allow for session" decisions.
 * For bash commands, we use the command name (first word) to allow
 * granularity like "bash:ls" vs "bash:rm".
 *
 * Examples:
 * - write → "write"
 * - edit → "edit"
 * - bash with "ls -la" → "bash:ls"
 * - bash with "rm -rf /tmp" → "bash:rm"
 * - bash with "git status" → "bash:git"
 */
public final class TrustKeyGenerator {

    private TrustKeyGenerator() {
        // Utility class
    }

    /**
     * Generate a trust cache key for a tool call.
     *
     * @param toolName The name of the tool being called
     * @param args The arguments passed to the tool
     * @return A string key for caching trust decisions
     */
    public static String getTrustKey(String toolName, Map<String, Object> args) {
        if (toolName == null) {
            return "unknown";
        }

        if ("bash".equals(toolName) && args != null) {
            Object commandObj = args.get("command");
            if (commandObj instanceof String command && !command.isBlank()) {
                // Extract the command name (first word)
                String cmdName = command.strip().split("\\s+")[0];
                return "bash:" + cmdName;
            }
        }

        return toolName;
    }

    /**
     * Generate a trust cache key for a tool call with context.
     *
     * @param toolName The name of the tool being called
     * @param command The bash command (if applicable)
     * @return A string key for caching trust decisions
     */
    public static String getTrustKey(String toolName, String command) {
        if (toolName == null) {
            return "unknown";
        }

        if ("bash".equals(toolName) && command != null && !command.isBlank()) {
            String cmdName = command.strip().split("\\s+")[0];
            return "bash:" + cmdName;
        }

        return toolName;
    }
}
