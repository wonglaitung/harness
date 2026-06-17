package com.harness.tools;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

import java.nio.file.Path;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

import com.harness.core.ToolContext;
import com.harness.types.ToolResult;

class ReadToolTest {

    @TempDir
    Path tempDir;

    @Test
    void testReadFile() throws Exception {
        // Create test file
        Path testFile = tempDir.resolve("test.txt");
        java.nio.file.Files.writeString(testFile, "Hello, World!");

        ReadTool tool = new ReadTool();
        ToolContext context = ToolContext.of(tempDir.toString(), "test-session");

        Map<String, Object> args = Map.of("file_path", testFile.toString());
        ToolResult result = tool.execute(args, context).join();

        assertTrue(result.success());
        assertTrue(result.content().contains("Hello, World!"));
    }

    @Test
    void testReadNonexistentFile() {
        ReadTool tool = new ReadTool();
        ToolContext context = ToolContext.of(tempDir.toString(), "test-session");

        Map<String, Object> args = Map.of("file_path", "/nonexistent/file.txt");
        ToolResult result = tool.execute(args, context).join();

        assertFalse(result.success());
        assertTrue(result.error().contains("does not exist"));
    }

    @Test
    void testValidation() {
        ReadTool tool = new ReadTool();

        // Missing file_path
        com.harness.core.ValidationResult result = tool.validate(Map.of());
        assertFalse(result.isValid());

        // Valid
        result = tool.validate(Map.of("file_path", "/tmp/test.txt"));
        assertTrue(result.isValid());
    }

    @Test
    void testReadWithLimit() throws Exception {
        Path testFile = tempDir.resolve("large.txt");
        java.nio.file.Files.writeString(testFile, "Line 1\nLine 2\nLine 3\nLine 4\nLine 5");

        ReadTool tool = new ReadTool();
        ToolContext context = ToolContext.of(tempDir.toString(), "test-session");

        Map<String, Object> args = Map.of(
            "file_path", testFile.toString(),
            "limit", 2
        );
        ToolResult result = tool.execute(args, context).join();

        assertTrue(result.success());
        assertTrue(result.content().contains("Line 1"));
        assertTrue(result.content().contains("Line 2"));
        // Should not contain Line 3
        assertFalse(result.content().contains("Line 3") || result.content().split("\n").length <= 3);
    }
}