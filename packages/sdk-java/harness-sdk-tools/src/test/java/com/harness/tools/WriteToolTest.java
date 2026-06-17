package com.harness.tools;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

import java.nio.file.Path;
import java.util.Map;

import com.harness.core.ToolContext;
import com.harness.types.ToolResult;

class WriteToolTest {

    @TempDir
    Path tempDir;

    @Test
    void testWriteFile() {
        WriteTool tool = new WriteTool();
        ToolContext context = ToolContext.of(tempDir.toString(), "test-session");

        Path targetFile = tempDir.resolve("output.txt");
        Map<String, Object> args = Map.of(
            "file_path", targetFile.toString(),
            "content", "Test content"
        );

        ToolResult result = tool.execute(args, context).join();

        assertTrue(result.success());
        assertTrue(java.nio.file.Files.exists(targetFile));
    }

    @Test
    void testWriteCreatesParentDirs() {
        WriteTool tool = new WriteTool();
        ToolContext context = ToolContext.of(tempDir.toString(), "test-session");

        Path targetFile = tempDir.resolve("subdir/nested/output.txt");
        Map<String, Object> args = Map.of(
            "file_path", targetFile.toString(),
            "content", "Nested content"
        );

        ToolResult result = tool.execute(args, context).join();

        assertTrue(result.success());
        assertTrue(java.nio.file.Files.exists(targetFile));
    }

    @Test
    void testValidation() {
        WriteTool tool = new WriteTool();

        // Missing required fields
        com.harness.core.ValidationResult result = tool.validate(Map.of("file_path", "/tmp/test.txt"));
        assertFalse(result.isValid());

        result = tool.validate(Map.of("content", "test"));
        assertFalse(result.isValid());

        // Valid
        result = tool.validate(Map.of("file_path", "/tmp/test.txt", "content", "content"));
        assertTrue(result.isValid());
    }
}