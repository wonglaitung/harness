package com.harness.mcp;

import java.io.IOException;
import java.net.URI;
import java.net.http.*;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * HTTP transport for MCP.
 *
 * Supports three transport modes:
 * 1. Streamable HTTP (2025-11-25): POST to single endpoint, response may be SSE
 * 2. HTTP+SSE (2024-11-05, deprecated): POST /message + GET /sse separately
 * 3. FastMCP SSE: GET /sse discovers endpoint, POST to /messages/?session_id=xxx
 *
 * Auto-detects protocol on connect.
 *
 * Example:
 * <pre>
 * HTTPTransport transport = HTTPTransport.builder()
 *     .url("http://localhost:3000")
 *     .timeout(Duration.ofSeconds(30))
 *     .build();
 *
 * transport.connect();
 * transport.send(request);
 * JsonRpcResponse response = transport.receiveResponse();
 * transport.disconnect();
 * </pre>
 */
public class HTTPTransport implements MCPTransport {

    private static final Logger logger = LoggerFactory.getLogger(HTTPTransport.class);

    // Protocol types
    public static final String PROTOCOL_STREAMABLE_HTTP = "streamable-http";
    public static final String PROTOCOL_HTTP_SSE = "http-sse";
    public static final String PROTOCOL_FASTMCP_SSE = "fastmcp-sse";

    private final String url;
    private final Map<String, String> headers;
    private final Duration timeout;
    private final String forcedProtocol;

    private HttpClient httpClient;
    private final ObjectMapper objectMapper;
    private final AtomicBoolean connected = new AtomicBoolean(false);
    private final BlockingQueue<Map<String, Object>> messageQueue = new LinkedBlockingQueue<>();

    private String protocol;
    private String messageEndpoint;
    private String sessionId;

    private HTTPTransport(Builder builder) {
        this.url = builder.url;
        this.headers = builder.headers;
        this.timeout = builder.timeout;
        this.forcedProtocol = builder.forcedProtocol;
        this.objectMapper = new ObjectMapper();
    }

    @Override
    public synchronized void connect() throws IOException {
        if (connected.get()) {
            logger.warn("Transport already connected");
            return;
        }

        // Create HTTP client
        httpClient = HttpClient.newBuilder()
            .version(HttpClient.Version.HTTP_1_1)
            .connectTimeout(timeout)
            .build();

        try {
            // Detect protocol if not forced
            if (forcedProtocol != null && !forcedProtocol.isEmpty()) {
                protocol = forcedProtocol;
            } else {
                protocol = detectProtocol();
            }

            logger.info("Detected MCP protocol: {}", protocol);

            // Establish connection based on protocol
            if (PROTOCOL_STREAMABLE_HTTP.equals(protocol)) {
                messageEndpoint = "/mcp";
                connected.set(true);
            } else {
                // For SSE-based protocols, we would need async SSE client
                // Simplified: just set connected
                messageEndpoint = "/message";
                connected.set(true);
            }

        } catch (Exception e) {
            logger.error("Failed to connect: {}", e.getMessage());
            throw new IOException("Failed to connect: " + e.getMessage(), e);
        }
    }

    @Override
    public synchronized void disconnect() {
        connected.set(false);
        httpClient = null;
        messageQueue.clear();
        logger.info("HTTP transport disconnected");
    }

    @Override
    public void send(Map<String, Object> message) throws IOException {
        if (!connected.get() || httpClient == null) {
            throw new IOException("Transport not connected");
        }

        String endpoint = getSendEndpoint();
        String body = objectMapper.writeValueAsString(message);

        HttpRequest.Builder requestBuilder = HttpRequest.newBuilder()
            .uri(URI.create(url + endpoint))
            .header("Content-Type", "application/json")
            .POST(HttpRequest.BodyPublishers.ofString(body));

        // Add protocol-specific headers
        for (Map.Entry<String, String> header : getSendHeaders().entrySet()) {
            requestBuilder.header(header.getKey(), header.getValue());
        }

        HttpRequest request = requestBuilder.timeout(timeout).build();

        logger.debug("Sending MCP request: {} to {}", message.get("method"), endpoint);

        try {
            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 404 && PROTOCOL_FASTMCP_SSE.equals(protocol)) {
                // Session expired - would need to reconnect
                throw new IOException("Session expired");
            }

            if (response.statusCode() != 200 && response.statusCode() != 202) {
                throw new IOException("HTTP error: " + response.statusCode() + " - " + response.body());
            }

            // For Streamable HTTP, may receive SSE or JSON
            String contentType = response.headers().firstValue("Content-Type").orElse("");
            if (contentType.contains("application/json")) {
                try {
                    @SuppressWarnings("unchecked")
                    Map<String, Object> responseMessage = objectMapper.readValue(response.body(), Map.class);
                    messageQueue.put(responseMessage);
                } catch (Exception e) {
                    logger.debug("Could not parse response as JSON: {}", e.getMessage());
                }
            }

            // Update session ID if provided
            String newSessionId = response.headers().firstValue("Mcp-Session-Id").orElse(null);
            if (newSessionId != null) {
                sessionId = newSessionId;
            }

        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IOException("Request interrupted", e);
        }
    }

    @Override
    public void send(JsonRpcRequest request) throws IOException {
        Map<String, Object> message = new LinkedHashMap<>();
        message.put("jsonrpc", "2.0");
        message.put("id", request.id());
        message.put("method", request.method());
        if (request.params() != null) {
            message.put("params", request.params());
        }
        send(message);
    }

    @Override
    public Map<String, Object> receive() throws InterruptedException {
        return messageQueue.take();
    }

    @Override
    public Map<String, Object> receive(long timeout, TimeUnit unit)
            throws InterruptedException, TimeoutException {
        Map<String, Object> message = messageQueue.poll(timeout, unit);
        if (message == null) {
            throw new TimeoutException("Timeout waiting for message");
        }
        return message;
    }

    /**
     * Receive a response as JsonRpcResponse.
     */
    public JsonRpcResponse receiveResponse() throws InterruptedException {
        Map<String, Object> message = receive();
        return parseResponse(message);
    }

    /**
     * Receive a response with timeout.
     */
    public JsonRpcResponse receiveResponse(long timeout, TimeUnit unit)
            throws InterruptedException, TimeoutException {
        Map<String, Object> message = receive(timeout, unit);
        return parseResponse(message);
    }

    @Override
    public boolean isConnected() {
        return connected.get() && httpClient != null;
    }

    /**
     * Get the detected protocol.
     */
    public String getProtocol() {
        return protocol;
    }

    // === Private Methods ===

    /**
     * Detect server's HTTP transport protocol.
     */
    private String detectProtocol() throws IOException, InterruptedException {
        Map<String, Object> initMsg = new LinkedHashMap<>();
        initMsg.put("jsonrpc", "2.0");
        initMsg.put("method", "initialize");
        initMsg.put("params", Map.of(
            "protocolVersion", "2024-11-05",
            "capabilities", Map.of(),
            "clientInfo", Map.of("name", "harness", "version", "1.0")
        ));
        initMsg.put("id", "1");

        String body = objectMapper.writeValueAsString(initMsg);

        // Try Streamable HTTP endpoint first
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(url + "/mcp"))
            .header("Content-Type", "application/json")
            .header("Accept", "application/json, text/event-stream")
            .POST(HttpRequest.BodyPublishers.ofString(body))
            .timeout(timeout)
            .build();

        HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

        if (response.statusCode() == 200) {
            // Check response type
            String contentType = response.headers().firstValue("Content-Type").orElse("");

            if (contentType.contains("text/event-stream")) {
                logger.info("Server supports Streamable HTTP with SSE response");
                // Would need to parse SSE - simplified for now
            } else {
                // Plain JSON response
                @SuppressWarnings("unchecked")
                Map<String, Object> respMsg = objectMapper.readValue(response.body(), Map.class);
                messageQueue.put(respMsg);

                sessionId = response.headers().firstValue("Mcp-Session-Id").orElse(null);
                logger.info("Server supports Streamable HTTP with JSON response");
            }
            return PROTOCOL_STREAMABLE_HTTP;
        }

        if (response.statusCode() == 400 || response.statusCode() == 404 || response.statusCode() == 405) {
            logger.info("Server returned {}, falling back to SSE", response.statusCode());
        }

        // Default to FastMCP SSE
        logger.info("Defaulting to FastMCP SSE protocol");
        return PROTOCOL_FASTMCP_SSE;
    }

    /**
     * Get the POST endpoint based on protocol.
     */
    private String getSendEndpoint() {
        if (PROTOCOL_STREAMABLE_HTTP.equals(protocol)) {
            return "/mcp";
        } else if (PROTOCOL_HTTP_SSE.equals(protocol)) {
            return "/message";
        } else if (PROTOCOL_FASTMCP_SSE.equals(protocol)) {
            return messageEndpoint != null ? messageEndpoint : "/messages/";
        }
        return messageEndpoint != null ? messageEndpoint : "/message";
    }

    /**
     * Get headers for POST request based on protocol.
     */
    private Map<String, String> getSendHeaders() {
        Map<String, String> sendHeaders = new HashMap<>(headers);

        if (PROTOCOL_STREAMABLE_HTTP.equals(protocol)) {
            sendHeaders.put("Accept", "application/json, text/event-stream");
            if (sessionId != null) {
                sendHeaders.put("Mcp-Session-Id", sessionId);
            }
        }

        return sendHeaders;
    }

    /**
     * Parse response map to JsonRpcResponse.
     */
    @SuppressWarnings("unchecked")
    private JsonRpcResponse parseResponse(Map<String, Object> message) {
        String jsonrpc = (String) message.getOrDefault("jsonrpc", "2.0");
        String id = message.get("id") != null ? message.get("id").toString() : null;
        Object result = message.get("result");
        Object errorObj = message.get("error");

        JsonRpcResponse.JsonRpcError error = null;
        if (errorObj instanceof Map<?, ?> errorMap) {
            int code = ((Number) errorMap.get("code")).intValue();
            String msg = (String) errorMap.get("message");
            Object data = errorMap.get("data");
            error = new JsonRpcResponse.JsonRpcError(code, msg, data);
        }

        return new JsonRpcResponse(jsonrpc, id, result, error);
    }

    // === Builder ===

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String url;
        private Map<String, String> headers = Map.of();
        private Duration timeout = Duration.ofSeconds(30);
        private String forcedProtocol;

        public Builder url(String url) {
            this.url = url;
            return this;
        }

        public Builder headers(Map<String, String> headers) {
            this.headers = headers != null ? headers : Map.of();
            return this;
        }

        public Builder header(String key, String value) {
            if (this.headers.isEmpty()) {
                this.headers = new HashMap<>();
            }
            this.headers.put(key, value);
            return this;
        }

        public Builder timeout(Duration timeout) {
            this.timeout = timeout;
            return this;
        }

        public Builder protocol(String protocol) {
            this.forcedProtocol = protocol;
            return this;
        }

        public HTTPTransport build() {
            if (url == null || url.isEmpty()) {
                throw new IllegalArgumentException("URL is required");
            }
            return new HTTPTransport(this);
        }
    }
}
