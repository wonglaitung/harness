package com.harness.tools.browser;

import com.harness.core.Tool;
import com.harness.core.ToolCategory;
import com.harness.core.ToolContext;
import com.harness.core.ValidationResult;
import com.harness.types.ToolResult;

import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * Close the browser instance.
 *
 * <p>Use this to cleanup resources when done with browser automation.</p>
 */
public class BrowserCloseTool implements Tool {

    public static final String NAME = "browser_close";

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public String description() {
        return "Close the browser instance and cleanup resources.";
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(),
            "required", java.util.List.of()
        );
    }

    @Override
    public ToolCategory category() {
        return ToolCategory.NETWORK;
    }

    @Override
    public ValidationResult validate(Map<String, Object> args) {
        return ValidationResult.valid();
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        return CompletableFuture.supplyAsync(() -> {
            try {
                BrowserManager.close();
                return ToolResult.success("", "✅ Browser closed", NAME);
            } catch (Exception e) {
                return ToolResult.failure("", "Close failed: " + e.getMessage(), NAME);
            }
        });
    }
}
