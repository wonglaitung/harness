package com.harness.mcp;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * MCP server manager.
 *
 * Manages configurations for MCP servers and provides tool discovery interface.
 *
 * Note: This implementation provides configuration management and placeholder methods.
 * Actual client connections require Kotlin SDK integration (see McpClientHelper.kt).
 */
public class McpManager {

    private static final Logger logger = LoggerFactory.getLogger(McpManager.class);

    private final Map<String, McpServerConfig> configs;
    private final Map<String, List<McpToolInfo>> serverTools;

    /**
     * Create manager.
     */
    public McpManager() {
        this.configs = new ConcurrentHashMap<>();
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
     * Note: This is a placeholder. Actual connection requires Kotlin SDK integration.
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

        // Placeholder - actual connection requires Kotlin SDK
        logger.warn("MCP client connection not yet implemented for server: {}", serverName);
        logger.info("To connect to MCP server, use McpClientHelper.kt or implement Kotlin SDK integration");
        return false;
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
     * Disconnect from a specific server.
     *
     * @param serverName Server name
     */
    public void disconnect(String serverName) {
        serverTools.remove(serverName);
        logger.info("Disconnected from MCP server: {}", serverName);
    }

    /**
     * Disconnect from all servers.
     */
    public void disconnectAll() {
        for (String serverName : new ArrayList<>(serverTools.keySet())) {
            disconnect(serverName);
        }
    }

    /**
     * Get all registered tool info (placeholder).
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
     * Check if connected to a server.
     *
     * @param serverName Server name
     * @return true if connected
     */
    public boolean isConnected(String serverName) {
        return serverTools.containsKey(serverName) && !serverTools.get(serverName).isEmpty();
    }

    /**
     * Get list of registered server names.
     */
    public List<String> getRegisteredServers() {
        return new ArrayList<>(configs.keySet());
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
}