package com.harness.core;

import java.util.Map;
import java.util.concurrent.CompletableFuture;

import com.harness.types.ToolResult;

/**
 * Tool interface.
 *
 * All tools must implement this interface.
 */
public interface Tool {

    /**
     * Tool name (unique identifier).
     */
    String name();

    /**
     * Tool description (for LLM understanding).
     */
    String description();

    /**
     * Input parameter schema (JSON Schema format).
     */
    Map<String, Object> inputSchema();

    /**
     * Execute the tool.
     *
     * @param args Input arguments
     * @param context Execution context
     * @return Execution result
     */
    CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context);

    /**
     * Validate arguments (optional implementation).
     *
     * @param args Input arguments
     * @return Validation result
     */
    default ValidationResult validate(Map<String, Object> args) {
        return ValidationResult.valid();
    }

    /**
     * Whether this tool is dangerous (requires explicit permission).
     */
    default boolean isDangerous() {
        return false;
    }

    /**
     * Tool category.
     */
    default ToolCategory category() {
        return ToolCategory.GENERAL;
    }

    /**
     * Convert to tool definition for LLM API.
     *
     * @return Tool definition map
     */
    default Map<String, Object> toDefinition() {
        return Map.of(
            "name", name(),
            "description", description(),
            "input_schema", inputSchema()
        );
    }
}