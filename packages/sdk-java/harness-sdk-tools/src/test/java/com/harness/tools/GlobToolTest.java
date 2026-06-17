package com.harness.tools;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

import java.nio.file.Path;
import java.util.Map;

import com.harness.core.ToolContext;
import com.harness.types.ToolResult;

class GlobToolTest {

    @TempDir
    Path tempDir;

    @Test
    void testGlobFindFiles() throws Exception {
        // Create test files
        java.nio.file.Files.writeString(tempDir.resolve("test1.java"), "content1");
        java.nio.file.Files.writeString(tempDir.resolve("test2.java"), "content2");
        java.nio.file.Files.writeString(tempDir.resolve("test.txt"), "text");

        GlobTool tool = new GlobTool();
        ToolContext context = ToolContext.of(tempDir.toString(), "test-session");

        Map<String, Object> args = Map.of("pattern", "*.java");
        ToolResult result = tool.execute(args, context).join();

        assertTrue(result.success());
        assertTrue(result.content().contains("test1.java"));
        assertTrue(result.content().contains("test2.java"));
        assertFalse(result.content().contains("test.txt"));
    }

    @Test
    void testGlobNoMatches() {
        GlobTool tool = new GlobTool();
        ToolContext context = ToolContext.of(tempDir.toString(), "test-session");

        Map<String, Object> args = Map.of("pattern", "*.nonexistent");
        ToolResult result = tool.execute(args, context).join();

        assertTrue(result.success());
        assertTrue(result.content().contains("No files"));
    }

    @Test
    void testValidation() {
        GlobTool tool = new GlobTool();

        // Missing pattern
        com.harness.core.ValidationResult result = tool.validate(Map.of());
        assertFalse(result.isValid());

        // Valid
        result = tool.validate(Map.of("pattern", "*.java"));
        assertTrue(result.isValid());
    }
}