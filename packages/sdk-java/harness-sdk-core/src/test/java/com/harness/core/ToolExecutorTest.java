package com.harness.core;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

import com.harness.types.Message;
import com.harness.types.Session;
import com.harness.types.ToolCall;
import com.harness.types.ToolResult;

class ToolExecutorTest {

    @Test
    void testToolRegistration() {
        ToolExecutor executor = new ToolExecutor();

        Tool tool = new SimpleTool();
        executor.registerTool(tool);

        assertTrue(executor.hasTool("simple"));
        assertEquals(1, executor.toolCount());
    }

    @Test
    void testToolExecution() {
        ToolExecutor executor = new ToolExecutor();
        executor.registerTool(new SimpleTool());

        ToolContext context = ToolContext.of("/tmp", "test-session");
        ToolCall call = new ToolCall("call-1", "simple", Map.of("input", "test"));

        ToolResult result = executor.executeTool(call, context).join();

        assertTrue(result.success());
        assertEquals("Processed: test", result.content());
    }

    @Test
    void testUnknownTool() {
        ToolExecutor executor = new ToolExecutor();
        ToolContext context = ToolContext.of("/tmp", "test-session");
        ToolCall call = new ToolCall("call-1", "unknown", Map.of());

        ToolResult result = executor.executeTool(call, context).join();

        assertFalse(result.success());
        assertTrue(result.error().contains("Unknown tool"));
    }

    @Test
    void testToolValidation() {
        ToolExecutor executor = new ToolExecutor();
        executor.registerTool(new ValidatingTool());

        ToolContext context = ToolContext.of("/tmp", "test-session");
        ToolCall call = new ToolCall("call-1", "validating", Map.of());

        ToolResult result = executor.executeTool(call, context).join();

        assertFalse(result.success());
        assertTrue(result.error().contains("required"));
    }

    // Helper test tools
    static class SimpleTool implements Tool {
        @Override
        public String name() { return "simple"; }

        @Override
        public String description() { return "Simple test tool"; }

        @Override
        public Map<String, Object> inputSchema() {
            return Map.of("type", "object",
                "properties", Map.of("input", Map.of("type", "string")));
        }

        @Override
        public java.util.concurrent.CompletableFuture<ToolResult> execute(
                Map<String, Object> args, ToolContext ctx) {
            String input = (String) args.getOrDefault("input", "");
            return java.util.concurrent.CompletableFuture.completedFuture(
                ToolResult.success("", "Processed: " + input, name()));
        }
    }

    static class ValidatingTool implements Tool {
        @Override
        public String name() { return "validating"; }

        @Override
        public String description() { return "Tool with validation"; }

        @Override
        public Map<String, Object> inputSchema() {
            return Map.of("type", "object",
                "properties", Map.of("value", Map.of("type", "string")),
                "required", java.util.List.of("value"));
        }

        @Override
        public ValidationResult validate(Map<String, Object> args) {
            if (!args.containsKey("value")) {
                return ValidationResult.invalid("value is required");
            }
            return ValidationResult.valid();
        }

        @Override
        public java.util.concurrent.CompletableFuture<ToolResult> execute(
                Map<String, Object> args, ToolContext ctx) {
            return java.util.concurrent.CompletableFuture.completedFuture(
                ToolResult.success("", "OK", name()));
        }
    }
}