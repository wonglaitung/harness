package com.harness.mcp;

import java.io.IOException;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

/**
 * MCP transport layer abstraction.
 *
 * Defines the interface for different transport mechanisms
 * (stdio, HTTP, WebSocket, etc.)
 */
public interface MCPTransport {

    /**
     * Establish connection to MCP server.
     *
     * @throws IOException If connection fails
     */
    void connect() throws IOException;

    /**
     * Close connection to MCP server.
     */
    void disconnect();

    /**
     * Send a JSON-RPC message.
     *
     * @param message JSON-RPC message to send
     * @throws IOException If send fails
     */
    void send(Map<String, Object> message) throws IOException;

    /**
     * Send a JsonRpcRequest.
     *
     * @param request Request to send
     * @throws IOException If send fails
     */
    void send(JsonRpcRequest request) throws IOException;

    /**
     * Receive a message (blocking).
     *
     * @return Received message
     * @throws InterruptedException If interrupted
     */
    Map<String, Object> receive() throws InterruptedException;

    /**
     * Receive a message with timeout.
     *
     * @param timeout Timeout value
     * @param unit Time unit
     * @return Received message
     * @throws InterruptedException If interrupted
     * @throws TimeoutException If timeout expires
     */
    Map<String, Object> receive(long timeout, TimeUnit unit)
        throws InterruptedException, TimeoutException;

    /**
     * Check if transport is connected.
     *
     * @return True if connected
     */
    boolean isConnected();
}
