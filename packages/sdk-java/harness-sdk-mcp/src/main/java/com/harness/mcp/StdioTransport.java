package com.harness.mcp;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.function.Consumer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * Standard input/output transport for MCP.
 *
 * Communicates with MCP server via subprocess stdin/stdout.
 * This is the most common transport for local MCP servers.
 *
 * Example:
 * <pre>
 * StdioTransport transport = StdioTransport.builder()
 *     .command("mcp-server-filesystem")
 *     .args(List.of("/path/to/root"))
 *     .build();
 *
 * transport.connect();
 * transport.send(request);
 * JsonRpcResponse response = transport.receive();
 * transport.disconnect();
 * </pre>
 */
public class StdioTransport {

    private static final Logger logger = LoggerFactory.getLogger(StdioTransport.class);

    private final String command;
    private final List<String> args;
    private final Map<String, String> env;
    private final ObjectMapper objectMapper;

    private Process process;
    private BufferedWriter writer;
    private BufferedReader reader;
    private BufferedReader errorReader;
    private final AtomicBoolean connected = new AtomicBoolean(false);
    private final BlockingQueue<Map<String, Object>> messageQueue = new LinkedBlockingQueue<>();
    private Thread readerThread;
    private Thread errorThread;
    private volatile boolean running = false;

    private StdioTransport(Builder builder) {
        this.command = builder.command;
        this.args = builder.args;
        this.env = builder.env;
        this.objectMapper = new ObjectMapper();
    }

    /**
     * Connect to MCP server by starting subprocess.
     */
    public synchronized void connect() throws IOException {
        if (connected.get()) {
            logger.warn("Transport already connected");
            return;
        }

        // Build command
        List<String> commandLine = new ArrayList<>();
        commandLine.add(command);
        commandLine.addAll(args);

        // Build process builder
        ProcessBuilder pb = new ProcessBuilder(commandLine);

        // Set environment
        Map<String, String> processEnv = pb.environment();
        processEnv.putAll(env);

        // Redirect error stream to separate stream
        pb.redirectErrorStream(false);

        logger.info("Starting MCP server: {}", String.join(" ", commandLine));

        try {
            process = pb.start();
        } catch (IOException e) {
            logger.error("Failed to start MCP server: {}", e.getMessage());
            throw e;
        }

        // Get streams
        writer = new BufferedWriter(new OutputStreamWriter(process.getOutputStream(), StandardCharsets.UTF_8));
        reader = new BufferedReader(new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8));
        errorReader = new BufferedReader(new InputStreamReader(process.getErrorStream(), StandardCharsets.UTF_8));

        // Start reader threads
        running = true;

        readerThread = new Thread(this::readMessages, "MCP-Stdio-Reader");
        readerThread.setDaemon(true);
        readerThread.start();

        errorThread = new Thread(this::readErrors, "MCP-Stdio-Error");
        errorThread.setDaemon(true);
        errorThread.start();

        connected.set(true);
        logger.info("MCP server started with PID: {}", process.pid());
    }

    /**
     * Disconnect from MCP server.
     */
    public synchronized void disconnect() {
        if (!connected.get()) {
            return;
        }

        running = false;
        connected.set(false);

        // Close writer first
        if (writer != null) {
            try {
                writer.close();
            } catch (IOException e) {
                // Ignore
            }
        }

        // Terminate process
        if (process != null && process.isAlive()) {
            process.destroy();

            try {
                if (!process.waitFor(5, TimeUnit.SECONDS)) {
                    process.destroyForcibly();
                    process.waitFor(1, TimeUnit.SECONDS);
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                process.destroyForcibly();
            }
        }

        // Interrupt threads
        if (readerThread != null) {
            readerThread.interrupt();
        }
        if (errorThread != null) {
            errorThread.interrupt();
        }

        // Clear queue
        messageQueue.clear();

        process = null;
        writer = null;
        reader = null;
        errorReader = null;

        logger.info("MCP server stopped");
    }

    /**
     * Send a JSON-RPC message.
     */
    public void send(Map<String, Object> message) throws IOException {
        if (!connected.get() || writer == null) {
            throw new IOException("Transport not connected");
        }

        String json = objectMapper.writeValueAsString(message) + "\n";

        synchronized (writer) {
            writer.write(json);
            writer.flush();
        }

        logger.debug("Sent message: {}", message.get("method"));
    }

    /**
     * Send a JsonRpcRequest.
     */
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

    /**
     * Receive a message (blocking).
     */
    public Map<String, Object> receive() throws InterruptedException {
        return messageQueue.take();
    }

    /**
     * Receive a message with timeout.
     */
    public Map<String, Object> receive(long timeout, TimeUnit unit) throws InterruptedException, TimeoutException {
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

    /**
     * Check if transport is connected.
     */
    public boolean isConnected() {
        return connected.get() && process != null && process.isAlive();
    }

    /**
     * Check stderr for errors.
     */
    public String checkErrors() {
        // Errors are logged asynchronously, check last few lines from error reader
        return ""; // Errors are logged via readErrors thread
    }

    /**
     * Send request and receive response (convenience method).
     */
    public JsonRpcResponse sendAndReceive(JsonRpcRequest request) throws IOException, InterruptedException {
        send(request);
        return receiveResponse();
    }

    /**
     * Send request and receive response with timeout.
     */
    public JsonRpcResponse sendAndReceive(JsonRpcRequest request, long timeout, TimeUnit unit)
            throws IOException, InterruptedException, TimeoutException {
        send(request);
        return receiveResponse(timeout, unit);
    }

    /**
     * Add a message listener.
     */
    public void addMessageListener(Consumer<Map<String, Object>> listener) {
        // For now, use polling via receive()
        // A more complete implementation would use a publisher-subscriber pattern
    }

    // === Private Methods ===

    /**
     * Read messages from stdout in background thread.
     */
    private void readMessages() {
        try {
            String line;
            while (running && (line = reader.readLine()) != null) {
                try {
                    @SuppressWarnings("unchecked")
                    Map<String, Object> message = objectMapper.readValue(line, Map.class);
                    messageQueue.put(message);
                    logger.debug("Received message: {}", message.get("method"));
                } catch (Exception e) {
                    logger.warn("Failed to parse message: {}", e.getMessage());
                }
            }
        } catch (IOException e) {
            if (running) {
                logger.error("Error reading from MCP server: {}", e.getMessage());
            }
        } finally {
            running = false;
            connected.set(false);
        }
    }

    /**
     * Read errors from stderr in background thread.
     */
    private void readErrors() {
        try {
            String line;
            while (running && (line = errorReader.readLine()) != null) {
                logger.warn("MCP server stderr: {}", line);
            }
        } catch (IOException e) {
            if (running) {
                logger.debug("Error reading stderr: {}", e.getMessage());
            }
        }
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
        private String command;
        private List<String> args = List.of();
        private Map<String, String> env = Map.of();

        public Builder command(String command) {
            this.command = command;
            return this;
        }

        public Builder args(List<String> args) {
            this.args = args != null ? args : List.of();
            return this;
        }

        public Builder args(String... args) {
            this.args = List.of(args);
            return this;
        }

        public Builder env(Map<String, String> env) {
            this.env = env != null ? env : Map.of();
            return this;
        }

        public Builder env(String key, String value) {
            if (this.env.isEmpty()) {
                this.env = new HashMap<>();
            }
            this.env.put(key, value);
            return this;
        }

        public StdioTransport build() {
            if (command == null || command.isEmpty()) {
                throw new IllegalArgumentException("Command is required");
            }
            return new StdioTransport(this);
        }
    }
}
