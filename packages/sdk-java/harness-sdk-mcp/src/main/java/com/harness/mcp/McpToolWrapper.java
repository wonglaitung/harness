package com.harness.mcp;

import java.util.Map;
import java.util.concurrent.CompletableFuture;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.core.Tool;
import com.harness.core.ToolContext;
import com.harness.core.ValidationResult;
import com.harness.types.ToolResult;

/**
 * Wrapper to expose MCP tools as Harness Tool interface.
 *
 * This allows MCP tools to be registered with AgentHarness
 * and used alongside native tools.
 *
 * Example:
 * <pre>
 * McpClient client = new McpClient("http://localhost:3000/mcp");
 * client.initialize().join();
 *
 * List<McpToolInfo> tools = client.listTools().join();
 * for (McpToolInfo info : tools) {
 *     Tool tool = new McpToolWrapper(client, info);
 *     agent.registerTool(tool);
 * }
 * </pre>
 */
public class McpToolWrapper implements Tool {

    private static final Logger logger = LoggerFactory.getLogger(McpToolWrapper.class);

    private final McpClient client;
    private final McpToolInfo toolInfo;

    /**
     * Create wrapper for an MCP tool.
     *
     * @param client The MCP client to use for calls
     * @param toolInfo The tool information from MCP server
     */
    public McpToolWrapper(McpClient client, McpToolInfo toolInfo) {
        this.client = client;
        this.toolInfo = toolInfo;
    }

    @Override
    public String name() {
        return toolInfo.fullName();
    }

    @Override
    public String description() {
        return toolInfo.shortDescription();
    }

    @Override
    public Map<String, Object> inputSchema() {
        return toolInfo.inputSchema();
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        logger.debug("Executing MCP tool: {} with args: {}", toolInfo.toolName(), args.keySet());

        return client.callTool(toolInfo.toolName(), args)
            .thenApply(mcpResult -> {
                if (mcpResult.isSuccess()) {
                    return ToolResult.success(
                        context != null ? context.sessionId() : "",
                        mcpResult.content(),
                        toolInfo.fullName()
                    );
                } else {
                    return ToolResult.failure(
                        context != null ? context.sessionId() : "",
                        mcpResult.contentOrError(),
                        toolInfo.fullName()
                    );
                }
            })
            .exceptionally(e -> {
                logger.error("MCP tool execution failed: {}", e.getMessage());
                return ToolResult.failure(
                    context != null ? context.sessionId() : "",
                    "Execution error: " + e.getMessage(),
                    toolInfo.fullName()
                );
            });
    }

    @Override
    public ValidationResult validate(Map<String, Object> args) {
        // Basic validation - check required properties from schema
        Map<String, Object> schema = toolInfo.inputSchema();
        if (schema == null || schema.isEmpty()) {
            return ValidationResult.valid();
        }

        Object requiredObj = schema.get("required");
        if (requiredObj instanceof java.util.List<?> required) {
            for (Object prop : required) {
                if (prop instanceof String propName && !args.containsKey(propName)) {
                    return ValidationResult.invalid("Missing required parameter: " + propName);
                }
            }
        }

        return ValidationResult.valid();
    }

    @Override
    public boolean isDangerous() {
        // MCP tools are considered potentially dangerous
        // since they may have access to external resources
        return true;
    }

    /**
     * Get the underlying MCP tool info.
     */
    public McpToolInfo toolInfo() {
        return toolInfo;
    }

    /**
     * Get the MCP client.
     */
    public McpClient client() {
        return client;
    }

    /**
     * Get the original tool name (without prefix).
     */
    public String originalName() {
        return toolInfo.toolName();
    }

    /**
     * Get the server name this tool belongs to.
     */
    public String serverName() {
        return toolInfo.serverName();
    }

    @Override
    public String toString() {
        return "McpToolWrapper{" + name() + "}";
    }
}