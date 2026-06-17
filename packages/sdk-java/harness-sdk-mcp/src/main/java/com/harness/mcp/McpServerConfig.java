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
    String command,
    List<String> args,
    Map<String, String> env,
    String url,
    McpTransportType transportType,
    Duration requestTimeout,
    boolean enabled
) {

    /**
     * Transport types for MCP connections.
     */
    public enum McpTransportType {
        STDIO,
        SSE
    }

    /**
     * Create config for stdio transport.
     */
    public static McpServerConfig stdio(String name, String command, String... args) {
        return new McpServerConfig(
            name,
            command,
            List.of(args),
            Map.of(),
            null,
            McpTransportType.STDIO,
            Duration.ofSeconds(30),
            true
        );
    }

    /**
     * Create config for SSE transport.
     */
    public static McpServerConfig sse(String name, String url) {
        return new McpServerConfig(
            name,
            null,
            List.of(),
            Map.of(),
            url,
            McpTransportType.SSE,
            Duration.ofSeconds(30),
            true
        );
    }

    /**
     * Create config with environment variables.
     */
    public McpServerConfig withEnv(Map<String, String> env) {
        return new McpServerConfig(
            name, command, args, env, url, transportType, requestTimeout, enabled
        );
    }

    /**
     * Create config with timeout.
     */
    public McpServerConfig withTimeout(Duration timeout) {
        return new McpServerConfig(
            name, command, args, env, url, transportType, timeout, enabled
        );
    }

    /**
     * Create disabled config.
     */
    public McpServerConfig disabled() {
        return new McpServerConfig(
            name, command, args, env, url, transportType, requestTimeout, false
        );
    }
}