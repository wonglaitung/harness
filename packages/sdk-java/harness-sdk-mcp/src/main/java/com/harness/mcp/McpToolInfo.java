package com.harness.mcp;

import java.util.Map;

/**
 * MCP tool information.
 *
 * Wraps MCP tool metadata for registration with Harness.
 */
public record McpToolInfo(
    String serverName,
    String toolName,
    String description,
    Map<String, Object> inputSchema
) {

    /**
     * Get the full tool name (prefixed with server name).
     */
    public String fullName() {
        return "mcp_" + serverName + "_" + toolName;
    }

    /**
     * Get a short description for display.
     */
    public String shortDescription() {
        if (description == null || description.isEmpty()) {
            return "MCP tool: " + toolName;
        }
        return description.length() > 200
            ? description.substring(0, 200) + "..."
            : description;
    }
}