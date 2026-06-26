package com.harness.mcp;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicBoolean;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * MCP HTTP client using JSON-RPC 2.0 over HTTP.
 *
 * Implements the MCP (Model Context Protocol) client for connecting
 * to MCP servers via HTTP/SSE transport.
 *
 * Example:
 * <pre>
 * McpClient client = new McpClient("http://localhost:3000/mcp");
 *
 * // Initialize
 * client.initialize().join();
 *
 * // List tools
 * List<McpToolInfo> tools = client.listTools().join();
 *
 * // Call tool
 * McpToolResult result = client.callTool("read_file", Map.of("path", "/tmp/test.txt")).join();
 *
 * // Cleanup
 * client.close();
 * </pre>
 */
public class McpClient {

    private static final Logger logger = LoggerFactory.getLogger(McpClient.class);

    private final String serverUrl;
    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;
    private final Duration timeout;
    private final AtomicBoolean initialized = new AtomicBoolean(false);
    private final String serverName;

    // Server capabilities
    private Map<String, Object> serverCapabilities = Map.of();
    private String protocolVersion = "unknown";

    /**
     * Create client with URL.
     */
    public McpClient(String serverUrl) {
        this(serverUrl, "mcp-server", Duration.ofSeconds(30));
    }

    /**
     * Create client with config.
     */
    public McpClient(McpServerConfig config) {
        this(config.url(), config.name(), config.requestTimeout());
    }

    /**
     * Create client with all parameters.
     */
    public McpClient(String serverUrl, String serverName, Duration timeout) {
        this.serverUrl = serverUrl;
        this.serverName = serverName;
        this.timeout = timeout;

        this.httpClient = HttpClient.newBuilder()
            .version(HttpClient.Version.HTTP_1_1)
            .connectTimeout(timeout)
            .build();

        this.objectMapper = new ObjectMapper();

        logger.info("MCP client created for: {}", serverUrl);
    }

    /**
     * Initialize connection with server.
     *
     * Sends initialize request and stores capabilities.
     */
    public CompletableFuture<Boolean> initialize() {
        if (initialized.get()) {
            logger.warn("Already initialized");
            return CompletableFuture.completedFuture(true);
        }

        JsonRpcRequest request = JsonRpcRequest.initialize();

        return sendRequestAsync(request)
            .thenApply(response -> {
                if (!response.isSuccess()) {
                    logger.error("Initialize failed: {}", response.errorMessage());
                    return false;
                }

                Map<String, Object> result = response.resultAsMap();

                // Extract capabilities
                Object caps = result.get("capabilities");
                if (caps instanceof Map<?, ?> map) {
                    serverCapabilities = (Map<String, Object>) map;
                }

                // Extract protocol version
                Object version = result.get("protocolVersion");
                if (version != null) {
                    protocolVersion = version.toString();
                }

                initialized.set(true);
                logger.info("MCP initialized: server={}, protocol={}, capabilities={}",
                    serverName, protocolVersion, serverCapabilities.keySet());

                return true;
            })
            .exceptionally(e -> {
                logger.error("Initialize exception: {}", e.getMessage());
                return false;
            });
    }

    /**
     * List available tools from server.
     */
    public CompletableFuture<List<McpToolInfo>> listTools() {
        if (!initialized.get()) {
            logger.warn("Client not initialized, initializing first...");
            return initialize()
                .thenCompose(success -> {
                    if (!success) {
                        return CompletableFuture.completedFuture(List.of());
                    }
                    return listToolsInternal();
                });
        }
        return listToolsInternal();
    }

    private CompletableFuture<List<McpToolInfo>> listToolsInternal() {
        JsonRpcRequest request = JsonRpcRequest.listTools();

        return sendRequestAsync(request)
            .thenApply(response -> {
                if (!response.isSuccess()) {
                    logger.error("List tools failed: {}", response.errorMessage());
                    return List.of();
                }

                Map<String, Object> result = response.resultAsMap();
                Object toolsObj = result.get("tools");

                List<McpToolInfo> tools = new ArrayList<>();
                if (toolsObj instanceof List<?> toolsList) {
                    for (Object toolObj : toolsList) {
                        if (toolObj instanceof Map<?, ?> toolMap) {
                            McpToolInfo info = parseToolInfo(toolMap);
                            tools.add(info);
                        }
                    }
                }

                logger.info("Found {} tools from {}", tools.size(), serverName);
                return tools;
            })
            .exceptionally(e -> {
                logger.error("List tools exception: {}", e.getMessage());
                return List.of();
            });
    }

    /**
     * Call a tool on the server.
     */
    public CompletableFuture<McpToolResult> callTool(String toolName, Map<String, Object> arguments) {
        if (!initialized.get()) {
            logger.warn("Client not initialized for tool call: {}", toolName);
            return CompletableFuture.completedFuture(
                McpToolResult.error("Client not initialized", null)
            );
        }

        JsonRpcRequest request = JsonRpcRequest.callTool(toolName, arguments);

        return sendRequestAsync(request)
            .thenApply(response -> {
                if (!response.isSuccess()) {
                    return McpToolResult.error(
                        response.errorMessage(),
                        response.error
                    );
                }

                Map<String, Object> result = response.resultAsMap();

                // Extract content
                Object contentObj = result.get("content");
                String content = extractContent(contentObj);

                // Check for error flag
                Object isErrorObj = result.get("isError");
                boolean isError = isErrorObj != null && Boolean.TRUE.equals(isErrorObj);

                return isError
                    ? McpToolResult.error(content, null)
                    : McpToolResult.success(content);
            })
            .exceptionally(e -> {
                logger.error("Tool call exception: {}", e.getMessage());
                return McpToolResult.error(e.getMessage(), null);
            });
    }

    /**
     * Ping the server to check connection.
     */
    public CompletableFuture<Boolean> ping() {
        JsonRpcRequest request = JsonRpcRequest.ping();

        return sendRequestAsync(request)
            .thenApply(response -> response.isSuccess())
            .exceptionally(e -> false);
    }

    /**
     * Check if client is initialized.
     */
    public boolean isInitialized() {
        return initialized.get();
    }

    /**
     * Get server name.
     */
    public String serverName() {
        return serverName;
    }

    /**
     * Get server capabilities.
     */
    public Map<String, Object> capabilities() {
        return serverCapabilities;
    }

    /**
     * Get protocol version.
     */
    public String protocolVersion() {
        return protocolVersion;
    }

    /**
     * Close client.
     */
    public void close() {
        initialized.set(false);
        logger.info("MCP client closed: {}", serverName);
    }

    // === Private Methods ===

    /**
     * Send request asynchronously.
     */
    private CompletableFuture<JsonRpcResponse> sendRequestAsync(JsonRpcRequest request) {
        return CompletableFuture.supplyAsync(() -> sendRequest(request));
    }

    /**
     * Send request synchronously.
     */
    private JsonRpcResponse sendRequest(JsonRpcRequest request) {
        try {
            String body = objectMapper.writeValueAsString(request);

            HttpRequest httpRequest = HttpRequest.newBuilder()
                .uri(URI.create(serverUrl))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(body))
                .timeout(timeout)
                .build();

            logger.debug("Sending MCP request: {} to {}", request.method(), serverUrl);

            HttpResponse<String> httpResponse = httpClient.send(
                httpRequest,
                HttpResponse.BodyHandlers.ofString()
            );

            if (httpResponse.statusCode() != 200) {
                logger.error("HTTP error: {} {}", httpResponse.statusCode(), httpResponse.body());
                return new JsonRpcResponse(
                    "2.0",
                    request.id(),
                    null,
                    new JsonRpcResponse.JsonRpcError(
                        httpResponse.statusCode(),
                        "HTTP error: " + httpResponse.statusCode(),
                        httpResponse.body()
                    )
                );
            }

            String responseBody = httpResponse.body();
            logger.debug("MCP response: {}", responseBody.length() > 500
                ? responseBody.substring(0, 500) + "..."
                : responseBody);

            return parseResponse(responseBody);

        } catch (IOException | InterruptedException e) {
            logger.error("Request failed: {}", e.getMessage());
            Thread.currentThread().interrupt();
            return new JsonRpcResponse(
                "2.0",
                request.id(),
                null,
                new JsonRpcResponse.JsonRpcError(-1, e.getMessage(), null)
            );
        }
    }

    /**
     * Parse JSON-RPC response.
     */
    private JsonRpcResponse parseResponse(String json) {
        try {
            Map<String, Object> map = objectMapper.readValue(json, Map.class);

            String jsonrpc = (String) map.getOrDefault("jsonrpc", "2.0");
            String id = (String) map.get("id");
            Object result = map.get("result");
            Object errorObj = map.get("error");

            JsonRpcResponse.JsonRpcError error = null;
            if (errorObj instanceof Map<?, ?> errorMap) {
                int code = ((Number) errorMap.get("code")).intValue();
                String message = (String) errorMap.get("message");
                Object data = errorMap.get("data");
                error = new JsonRpcResponse.JsonRpcError(code, message, data);
            }

            return new JsonRpcResponse(jsonrpc, id, result, error);

        } catch (Exception e) {
            logger.error("Failed to parse response: {}", e.getMessage());
            return new JsonRpcResponse(
                "2.0",
                null,
                null,
                new JsonRpcResponse.JsonRpcError(-32700, "Parse error: " + e.getMessage(), json)
            );
        }
    }

    /**
     * Parse tool info from response.
     */
    private McpToolInfo parseToolInfo(Map<?, ?> toolMap) {
        String name = (String) toolMap.get("name");
        String description = (String) toolMap.getOrDefault("description", "");

        Object inputSchemaObj = toolMap.get("inputSchema");
        Map<String, Object> inputSchema = Map.of();
        if (inputSchemaObj instanceof Map<?, ?> schemaMap) {
            inputSchema = (Map<String, Object>) schemaMap;
        }

        return new McpToolInfo(serverName, name, description, inputSchema);
    }

    /**
     * Extract content from tool result.
     */
    private String extractContent(Object contentObj) {
        if (contentObj == null) {
            return "";
        }

        if (contentObj instanceof String str) {
            return str;
        }

        if (contentObj instanceof List<?> contentList) {
            StringBuilder sb = new StringBuilder();
            for (Object item : contentList) {
                if (item instanceof Map<?, ?> itemMap) {
                    Object type = itemMap.get("type");
                    Object text = itemMap.get("text");
                    if ("text".equals(type) && text != null) {
                        sb.append(text.toString());
                    }
                } else if (item instanceof String str) {
                    sb.append(str);
                }
            }
            return sb.toString();
        }

        return contentObj.toString();
    }
}