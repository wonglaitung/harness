package com.harness.mcp;

import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

import com.harness.core.Tool;
import com.harness.core.ToolCategory;
import com.harness.core.ToolContext;
import com.harness.core.ValidationResult;
import com.harness.types.ToolResult;

import io.modelcontextprotocol.java.sdk.McpSyncClient;
import io.modelcontextprotocol.java.sdk.CallToolRequest;
import io.modelcontextprotocol.java.sdk.CallToolResult;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Wrapper to expose MCP tools as Harness Tools.
 *
 * Adapts MCP tool protocol to Harness Tool interface.
 */
public class McpToolWrapper implements Tool {

    private static final Logger logger = LoggerFactory.getLogger(McpToolWrapper.class);

    private final McpSyncClient client;
    private final McpToolInfo toolInfo;

    /**
     * Create wrapper for an MCP tool.
     *
     * @param client MCP client
     * @param toolInfo Tool information
     */
    public McpToolWrapper(McpSyncClient client, McpToolInfo toolInfo) {
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
    public ToolCategory category() {
        return ToolCategory.MCP;
    }

    @Override
    public ValidationResult validate(Map<String, Object> args) {
        // Basic validation - MCP handles schema validation
        return ValidationResult.valid();
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                logger.debug("Calling MCP tool: {} with args: {}", toolInfo.toolName(), args);

                CallToolRequest request = new CallToolRequest(toolInfo.toolName(), args);
                CallToolResult result = client.callTool(request);

                // Extract content from result
                String output = extractContent(result);

                if (result.isError() != null && result.isError()) {
                    logger.warn("MCP tool {} returned error: {}", toolInfo.toolName(), output);
                    return ToolResult.failure("", output, name());
                }

                logger.debug("MCP tool {} executed successfully", toolInfo.toolName());
                return ToolResult.success("", output, name());

            } catch (Exception e) {
                logger.error("MCP tool {} execution failed: {}", toolInfo.toolName(), e.getMessage());
                return ToolResult.failure("", "MCP tool error: " + e.getMessage(), name());
            }
        });
    }

    /**
     * Extract text content from MCP result.
     */
    private String extractContent(CallToolResult result) {
        if (result.content() == null || result.content().isEmpty()) {
            return "";
        }

        StringBuilder sb = new StringBuilder();
        for (Object content : result.content()) {
            if (content instanceof Map) {
                @SuppressWarnings("unchecked")
                Map<String, Object> contentMap = (Map<String, Object>) content;
                Object text = contentMap.get("text");
                if (text != null) {
                    sb.append(text.toString());
                }
            } else {
                sb.append(content.toString());
            }
        }

        return sb.toString();
    }

    /**
     * Get the server name.
     */
    public String serverName() {
        return toolInfo.serverName();
    }

    /**
     * Get the original MCP tool name.
     */
    public String mcpToolName() {
        return toolInfo.toolName();
    }
}