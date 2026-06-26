package com.harness.mcp;

import java.time.Duration;
import java.util.List;
import java.util.Map;

/**
 * MCP server configuration.
 *
 * Defines how to connect to an MCP server.
 */
public record McpServerConfig(
    String name,
    String url,
    McpTransportType transportType,
    Duration requestTimeout,
    boolean enabled
) {

    /**
     * Transport types for MCP connections.
     */
    public enum McpTransportType {
        SSE,  // HTTP Server-Sent Events (recommended)
        STDIO // Process-based (requires native process management)
    }

    /**
     * Create config for SSE/HTTP transport.
     *
     * @param name Server name
     * @param url Server URL (e.g., "http://localhost:3000/mcp")
     */
    public static McpServerConfig sse(String name, String url) {
        return new McpServerConfig(
            name,
            url,
            McpTransportType.SSE,
            Duration.ofSeconds(30),
            true
        );
    }

    /**
     * Create config with timeout.
     */
    public McpServerConfig withTimeout(Duration timeout) {
        return new McpServerConfig(name, url, transportType, timeout, enabled);
    }

    /**
     * Create disabled config.
     */
    public McpServerConfig disabled() {
        return new McpServerConfig(name, url, transportType, requestTimeout, false);
    }
}