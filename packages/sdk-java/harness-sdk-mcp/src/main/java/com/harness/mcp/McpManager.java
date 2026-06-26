package com.harness.mcp;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * MCP server manager.
 *
 * Manages connections to MCP servers and provides tool discovery.
 *
 * Features:
 * - Server registration and connection management
 * - Tool discovery from connected servers
 * - Tool registration with AgentHarness
 *
 * Example:
 * <pre>
 * McpManager manager = new McpManager();
 *
 * // Register server
 * manager.registerServer(McpServerConfig.sse("filesystem", "http://localhost:3000/mcp"));
 *
 * // Connect
 * boolean connected = manager.connect("filesystem");
 *
 * // Get tools
 * List<McpToolInfo> tools = manager.getServerToolInfos("filesystem");
 *
 * // Get as Harness Tools
 * List<Tool> harnessTools = manager.getHarnessTools("filesystem");
 * </pre>
 */
public class McpManager {

    private static final Logger logger = LoggerFactory.getLogger(McpManager.class);

    private final Map<String, McpServerConfig> configs;
    private final Map<String, McpClient> clients;
    private final Map<String, List<McpToolInfo>> serverTools;

    /**
     * Create manager.
     */
    public McpManager() {
        this.configs = new ConcurrentHashMap<>();
        this.clients = new ConcurrentHashMap<>();
        this.serverTools = new ConcurrentHashMap<>();
    }

    /**
     * Register an MCP server configuration.
     *
     * @param config Server configuration
     */
    public void registerServer(McpServerConfig config) {
        configs.put(config.name(), config);
        logger.info("Registered MCP server config: {}", config.name());
    }

    /**
     * Register multiple server configurations.
     *
     * @param configs Server configurations
     */
    public void registerServers(List<McpServerConfig> configs) {
        for (McpServerConfig config : configs) {
            registerServer(config);
        }
    }

    /**
     * Connect to a specific server.
     *
     * @param serverName Server name
     * @return true if connected successfully
     */
    public boolean connect(String serverName) {
        McpServerConfig config = configs.get(serverName);
        if (config == null) {
            logger.error("Server config not found: {}", serverName);
            return false;
        }

        if (!config.enabled()) {
            logger.info("Server {} is disabled, skipping", serverName);
            return false;
        }

        // Check if already connected
        if (clients.containsKey(serverName)) {
            McpClient existingClient = clients.get(serverName);
            if (existingClient.isInitialized()) {
                logger.debug("Already connected to: {}", serverName);
                return true;
            }
        }

        try {
            // Create client
            McpClient client = new McpClient(config);

            // Initialize synchronously
            Boolean success = client.initialize().join();
            if (!success) {
                logger.error("Failed to initialize MCP client for: {}", serverName);
                return false;
            }

            // Store client
            clients.put(serverName, client);

            // Discover tools
            List<McpToolInfo> tools = client.listTools().join();
            serverTools.put(serverName, tools);

            logger.info("Connected to MCP server: {} ({} tools)", serverName, tools.size());
            return true;

        } catch (Exception e) {
            logger.error("Failed to connect to MCP server {}: {}", serverName, e.getMessage());
            return false;
        }
    }

    /**
     * Connect to all registered servers.
     *
     * @return Map of server name to connection success
     */
    public Map<String, Boolean> connectAll() {
        Map<String, Boolean> results = new HashMap<>();
        for (String serverName : configs.keySet()) {
            results.put(serverName, connect(serverName));
        }
        return results;
    }

    /**
     * Connect to all servers asynchronously.
     */
    public CompletableFuture<Map<String, Boolean>> connectAllAsync() {
        return CompletableFuture.supplyAsync(this::connectAll);
    }

    /**
     * Disconnect from a specific server.
     *
     * @param serverName Server name
     */
    public void disconnect(String serverName) {
        McpClient client = clients.remove(serverName);
        if (client != null) {
            client.close();
        }
        serverTools.remove(serverName);
        logger.info("Disconnected from MCP server: {}", serverName);
    }

    /**
     * Disconnect from all servers.
     */
    public void disconnectAll() {
        for (String serverName : new ArrayList<>(clients.keySet())) {
            disconnect(serverName);
        }
    }

    /**
     * Get all registered tool info.
     *
     * @return List of all MCP tool info
     */
    public List<McpToolInfo> getAllToolInfos() {
        List<McpToolInfo> allTools = new ArrayList<>();
        for (List<McpToolInfo> tools : serverTools.values()) {
            allTools.addAll(tools);
        }
        return allTools;
    }

    /**
     * Get tools info from a specific server.
     *
     * @param serverName Server name
     * @return List of tool info from the server
     */
    public List<McpToolInfo> getServerToolInfos(String serverName) {
        return serverTools.getOrDefault(serverName, List.of());
    }

    /**
     * Get a specific tool info.
     *
     * @param toolName Full tool name (mcp_servername_toolname)
     * @return Tool info or null
     */
    public McpToolInfo getToolInfo(String toolName) {
        for (List<McpToolInfo> tools : serverTools.values()) {
            for (McpToolInfo tool : tools) {
                if (tool.fullName().equals(toolName)) {
                    return tool;
                }
            }
        }
        return null;
    }

    /**
     * Get Harness Tool wrappers for all tools from a server.
     *
     * @param serverName Server name
     * @return List of Tool wrappers
     */
    public List<com.harness.core.Tool> getHarnessTools(String serverName) {
        McpClient client = clients.get(serverName);
        List<McpToolInfo> tools = serverTools.getOrDefault(serverName, List.of());

        List<com.harness.core.Tool> harnessTools = new ArrayList<>();
        for (McpToolInfo tool : tools) {
            harnessTools.add(new McpToolWrapper(client, tool));
        }
        return harnessTools;
    }

    /**
     * Get all Harness Tool wrappers from all connected servers.
     */
    public List<com.harness.core.Tool> getAllHarnessTools() {
        List<com.harness.core.Tool> allTools = new ArrayList<>();
        for (String serverName : clients.keySet()) {
            allTools.addAll(getHarnessTools(serverName));
        }
        return allTools;
    }

    /**
     * Get MCP client for a server.
     *
     * @param serverName Server name
     * @return Client or null if not connected
     */
    public McpClient getClient(String serverName) {
        return clients.get(serverName);
    }

    /**
     * Check if connected to a server.
     *
     * @param serverName Server name
     * @return true if connected
     */
    public boolean isConnected(String serverName) {
        McpClient client = clients.get(serverName);
        return client != null && client.isInitialized();
    }

    /**
     * Get list of registered server names.
     */
    public List<String> getRegisteredServers() {
        return new ArrayList<>(configs.keySet());
    }

    /**
     * Get list of connected server names.
     */
    public List<String> getConnectedServers() {
        List<String> connected = new ArrayList<>();
        for (String serverName : clients.keySet()) {
            if (isConnected(serverName)) {
                connected.add(serverName);
            }
        }
        return connected;
    }

    /**
     * Get server status summary.
     */
    public Map<String, String> getStatus() {
        Map<String, String> status = new HashMap<>();
        for (String serverName : configs.keySet()) {
            if (isConnected(serverName)) {
                int toolCount = serverTools.getOrDefault(serverName, List.of()).size();
                status.put(serverName, "connected (" + toolCount + " tools)");
            } else if (configs.get(serverName).enabled()) {
                status.put(serverName, "disconnected");
            } else {
                status.put(serverName, "disabled");
            }
        }
        return status;
    }

    /**
     * Get config for a server.
     *
     * @param serverName Server name
     * @return Server config or null
     */
    public McpServerConfig getConfig(String serverName) {
        return configs.get(serverName);
    }

    /**
     * Get statistics.
     */
    public Map<String, Object> getStats() {
        int totalTools = serverTools.values().stream()
            .mapToInt(List::size)
            .sum();

        return Map.of(
            "registeredServers", configs.size(),
            "connectedServers", clients.size(),
            "totalTools", totalTools,
            "servers", getStatus()
        );
    }
}