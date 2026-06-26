package com.harness.core;

import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

import com.harness.types.ToolCall;
import com.harness.types.ToolResult;

class ToolExecutorTest {

    @Test
    void testToolRegistration() {
        ToolExecutor executor = new ToolExecutor(List.of());

        Tool tool = new SimpleTool();
        executor.registerTool(tool);

        List<Tool> tools = executor.listTools();
        assertEquals(1, tools.size());
    }

    @Test
    void testToolExecution() {
        ToolExecutor executor = new ToolExecutor(List.of(new SimpleTool()));

        ToolContext context = ToolContext.builder()
            .workingDirectory("/tmp")
            .sessionId("test-session")
            .build();
        ToolCall call = new ToolCall("call-1", "simple", Map.of("input", "test"));

        ToolResult result = executor.execute(call, context).join();

        assertTrue(result.success());
        assertEquals("Processed: test", result.content());
    }

    @Test
    void testUnknownTool() {
        ToolExecutor executor = new ToolExecutor(List.of());
        ToolContext context = ToolContext.builder()
            .workingDirectory("/tmp")
            .sessionId("test-session")
            .build();
        ToolCall call = new ToolCall("call-1", "unknown", Map.of());

        ToolResult result = executor.execute(call, context).join();

        assertFalse(result.success());
        assertTrue(result.error().contains("Unknown tool"));
    }

    @Test
    void testToolValidation() {
        ToolExecutor executor = new ToolExecutor(List.of(new ValidatingTool()));

        ToolContext context = ToolContext.builder()
            .workingDirectory("/tmp")
            .sessionId("test-session")
            .build();
        ToolCall call = new ToolCall("call-1", "validating", Map.of());

        ToolResult result = executor.execute(call, context).join();

        assertFalse(result.success());
        assertTrue(result.error().contains("Validation failed"));
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
        public CompletableFuture<ToolResult> execute(
                Map<String, Object> args, ToolContext ctx) {
            String input = (String) args.getOrDefault("input", "");
            return CompletableFuture.completedFuture(
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
                "required", List.of("value"));
        }

        @Override
        public ValidationResult validate(Map<String, Object> args) {
            if (!args.containsKey("value")) {
                return ValidationResult.invalid("value is required");
            }
            return ValidationResult.valid();
        }

        @Override
        public CompletableFuture<ToolResult> execute(
                Map<String, Object> args, ToolContext ctx) {
            return CompletableFuture.completedFuture(
                ToolResult.success("", "OK", name()));
        }
    }
}
