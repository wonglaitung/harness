package com.harness.mcp;

import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import io.modelcontextprotocol.java.sdk.McpSyncClient;
import io.modelcontextprotocol.java.sdk.McpClient;
import io.modelcontextprotocol.java.sdk.ServerParameters;
import io.modelcontextprotocol.java.sdk.ListToolsResult;
import io.modelcontextprotocol.java.sdk.Tool;
import io.modelcontextprotocol.java.sdk.ClientCapabilities;
import io.modelcontextprotocol.java.sdk.transport.McpTransport;

import com.harness.core.ToolCategory;

/**
 * MCP server manager.
 *
 * Manages connections to multiple MCP servers and discovers their tools.
 */
public class McpManager {

    private static final Logger logger = LoggerFactory.getLogger(McpManager.class);

    private final Map<String, McpSyncClient> clients;
    private final Map<String, McpServerConfig> configs;
    private final Map<String, List<McpToolWrapper>> serverTools;

    /**
     * Create manager.
     */
    public McpManager() {
        this.clients = new ConcurrentHashMap<>();
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

        try {
            McpSyncClient client = createClient(config);
            client.initialize();

            clients.put(serverName, client);

            // Discover tools
            discoverTools(serverName, client);

            logger.info("Connected to MCP server: {}", serverName);
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
     * Disconnect from a specific server.
     *
     * @param serverName Server name
     */
    public void disconnect(String serverName) {
        McpSyncClient client = clients.remove(serverName);
        if (client != null) {
            try {
                client.closeGracefully();
                logger.info("Disconnected from MCP server: {}", serverName);
            } catch (Exception e) {
                logger.warn("Error disconnecting from MCP server {}: {}", serverName, e.getMessage());
            }
        }
        serverTools.remove(serverName);
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
     * Get all discovered tools.
     *
     * @return List of all MCP tool wrappers
     */
    public List<McpToolWrapper> getAllTools() {
        List<McpToolWrapper> allTools = new ArrayList<>();
        for (List<McpToolWrapper> tools : serverTools.values()) {
            allTools.addAll(tools);
        }
        return allTools;
    }

    /**
     * Get tools from a specific server.
     *
     * @param serverName Server name
     * @return List of tools from the server
     */
    public List<McpToolWrapper> getServerTools(String serverName) {
        return serverTools.getOrDefault(serverName, List.of());
    }

    /**
     * Get a specific tool.
     *
     * @param toolName Full tool name (mcp_servername_toolname)
     * @return Tool wrapper or null
     */
    public McpToolWrapper getTool(String toolName) {
        for (List<McpToolWrapper> tools : serverTools.values()) {
            for (McpToolWrapper tool : tools) {
                if (tool.name().equals(toolName)) {
                    return tool;
                }
            }
        }
        return null;
    }

    /**
     * Get client for a server.
     *
     * @param serverName Server name
     * @return MCP client or null
     */
    public McpSyncClient getClient(String serverName) {
        return clients.get(serverName);
    }

    /**
     * Check if connected to a server.
     *
     * @param serverName Server name
     * @return true if connected
     */
    public boolean isConnected(String serverName) {
        return clients.containsKey(serverName);
    }

    /**
     * Get list of connected server names.
     */
    public List<String> getConnectedServers() {
        return new ArrayList<>(clients.keySet());
    }

    /**
     * Get server status summary.
     */
    public Map<String, String> getStatus() {
        Map<String, String> status = new HashMap<>();
        for (String serverName : configs.keySet()) {
            if (clients.containsKey(serverName)) {
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
     * Create MCP client based on transport type.
     */
    private McpSyncClient createClient(McpServerConfig config) {
        McpTransport transport;

        if (config.transportType() == McpServerConfig.McpTransportType.SSE) {
            // SSE transport
            transport = new io.modelcontextprotocol.java.sdk.transport.HttpClientSseClientTransport(config.url());
        } else {
            // STDIO transport
            ServerParameters params = ServerParameters.builder(config.command())
                .args(config.args().toArray(new String[0]))
                .build();
            transport = new io.modelcontextprotocol.java.sdk.transport.StdioClientTransport(params);
        }

        Duration timeout = config.requestTimeout() != null ? config.requestTimeout() : Duration.ofSeconds(30);

        return McpClient.sync(transport)
            .requestTimeout(timeout)
            .capabilities(ClientCapabilities.builder()
                .roots(true)
                .build())
            .build();
    }

    /**
     * Discover tools from a connected server.
     */
    private void discoverTools(String serverName, McpSyncClient client) {
        try {
            ListToolsResult result = client.listTools();
            List<McpToolWrapper> tools = new ArrayList<>();

            if (result.tools() != null) {
                for (Tool tool : result.tools()) {
                    McpToolInfo toolInfo = new McpToolInfo(
                        serverName,
                        tool.name(),
                        tool.description(),
                        tool.inputSchema() != null ? tool.inputSchema() : Map.of()
                    );

                    McpToolWrapper wrapper = new McpToolWrapper(client, toolInfo);
                    tools.add(wrapper);

                    logger.debug("Discovered MCP tool: {} from {}", tool.name(), serverName);
                }
            }

            serverTools.put(serverName, tools);
            logger.info("Discovered {} tools from {}", tools.size(), serverName);

        } catch (Exception e) {
            logger.error("Failed to discover tools from {}: {}", serverName, e.getMessage());
            serverTools.put(serverName, List.of());
        }
    }
}