package com.harness.mcp;

import java.util.Map;
import java.util.UUID;

/**
 * JSON-RPC 2.0 request.
 *
 * MCP uses JSON-RPC 2.0 for communication.
 */
public record JsonRpcRequest(
    String jsonrpc,
    String id,
    String method,
    Map<String, Object> params
) {

    /**
     * JSON-RPC version.
     */
    public static final String VERSION = "2.0";

    /**
     * Create a request with auto-generated ID.
     */
    public static JsonRpcRequest create(String method, Map<String, Object> params) {
        return new JsonRpcRequest(
            VERSION,
            UUID.randomUUID().toString(),
            method,
            params != null ? params : Map.of()
        );
    }

    /**
     * Create a request with specific ID.
     */
    public static JsonRpcRequest create(String id, String method, Map<String, Object> params) {
        return new JsonRpcRequest(VERSION, id, method, params != null ? params : Map.of());
    }

    /**
     * Create initialize request.
     */
    public static JsonRpcRequest initialize() {
        return create("initialize", Map.of(
            "protocolVersion", "2024-11-05",
            "capabilities", Map.of(
                "tools", Map.of("listChanged", true)
            ),
            "clientInfo", Map.of(
                "name", "harness-sdk",
                "version", "0.1.0"
            )
        ));
    }

    /**
     * Create tools/list request.
     */
    public static JsonRpcRequest listTools() {
        return create("tools/list", Map.of());
    }

    /**
     * Create tools/call request.
     */
    public static JsonRpcRequest callTool(String toolName, Map<String, Object> arguments) {
        return create("tools/call", Map.of(
            "name", toolName,
            "arguments", arguments != null ? arguments : Map.of()
        ));
    }

    /**
     * Create ping request.
     */
    public static JsonRpcRequest ping() {
        return create("ping", Map.of());
    }
}