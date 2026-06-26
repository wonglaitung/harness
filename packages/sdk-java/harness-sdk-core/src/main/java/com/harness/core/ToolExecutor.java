package com.harness.core;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

import com.harness.types.ToolCall;
import com.harness.types.ToolResult;

/**
 * Tool executor - responsible for scheduling and executing tools.
 */
public class ToolExecutor {

    private final Map<String, Tool> tools;
    private final ExecutorService executor;
    private final long defaultTimeoutMs;

    public ToolExecutor(List<Tool> tools, long defaultTimeoutMs) {
        this.tools = new HashMap<>();
        for (Tool tool : tools) {
            this.tools.put(tool.name(), tool);
        }
        this.executor = Executors.newCachedThreadPool();
        this.defaultTimeoutMs = defaultTimeoutMs;
    }

    public ToolExecutor(List<Tool> tools) {
        this(tools, 30_000L); // Default 30 seconds
    }

    /**
     * Execute a single tool.
     */
    public CompletableFuture<ToolResult> execute(ToolCall call, ToolContext context) {
        Tool tool = tools.get(call.name());
        if (tool == null) {
            return CompletableFuture.completedFuture(
                ToolResult.failure(call.id(), "Unknown tool: " + call.name(), call.name())
            );
        }

        // Validate arguments
        ValidationResult validation = tool.validate(call.arguments());
        if (!validation.isValid()) {
            return CompletableFuture.completedFuture(
                ToolResult.failure(call.id(), "Validation failed: " + validation.error(), call.name())
            );
        }

        // Execute with timeout
        return tool.execute(call.arguments(), context)
            .orTimeout(defaultTimeoutMs, TimeUnit.MILLISECONDS)
            .exceptionally(e -> ToolResult.failure(call.id(), "Execution timeout/error: " + e.getMessage(), call.name()))
            .thenApply(result -> {
                // Add tool name to result if not present
                if (result.toolName() == null) {
                    return new ToolResult(
                        result.toolCallId(), result.success(), result.content(),
                        result.error(), call.name(), result.metadata()
                    );
                }
                return result;
            });
    }

    /**
     * Execute multiple tools in parallel.
     */
    public CompletableFuture<List<ToolResult>> executeAll(List<ToolCall> calls, ToolContext context) {
        List<CompletableFuture<ToolResult>> futures = calls.stream()
            .map(call -> execute(call, context))
            .toList();

        return CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]))
            .thenApply(v -> futures.stream()
                .map(CompletableFuture::join)
                .toList());
    }

    /**
     * List all registered tools.
     */
    public List<Tool> listTools() {
        return new ArrayList<>(tools.values());
    }

    /**
     * Register a new tool.
     */
    public void registerTool(Tool tool) {
        tools.put(tool.name(), tool);
    }

    /**
     * Check if a tool is registered.
     */
    public boolean hasTool(String name) {
        return tools.containsKey(name);
    }

    /**
     * Get a tool by name.
     */
    public Tool getTool(String name) {
        return tools.get(name);
    }

    /**
     * Shutdown executor.
     */
    public void shutdown() {
        executor.shutdown();
    }
}