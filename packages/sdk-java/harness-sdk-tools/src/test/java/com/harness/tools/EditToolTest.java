package com.harness.tools;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

import java.nio.file.Path;
import java.util.Map;

import com.harness.core.ToolContext;
import com.harness.types.ToolResult;

class EditToolTest {

    @TempDir
    Path tempDir;

    @Test
    void testEditReplace() throws Exception {
        Path testFile = tempDir.resolve("edit.txt");
        java.nio.file.Files.writeString(testFile, "Hello World");

        EditTool tool = new EditTool();
        ToolContext context = ToolContext.of(tempDir.toString(), "test-session");

        Map<String, Object> args = Map.of(
            "file_path", testFile.toString(),
            "old_string", "World",
            "new_string", "Java"
        );

        ToolResult result = tool.execute(args, context).join();

        assertTrue(result.success());
        assertEquals("Hello Java", java.nio.file.Files.readString(testFile));
    }

    @Test
    void testEditNotFound() throws Exception {
        Path testFile = tempDir.resolve("edit.txt");
        java.nio.file.Files.writeString(testFile, "Hello World");

        EditTool tool = new EditTool();
        ToolContext context = ToolContext.of(tempDir.toString(), "test-session");

        Map<String, Object> args = Map.of(
            "file_path", testFile.toString(),
            "old_string", "NotFound",
            "new_string", "Replaced"
        );

        ToolResult result = tool.execute(args, context).join();

        assertFalse(result.success());
        assertTrue(result.error().contains("not found"));
    }

    @Test
    void testEditMultipleMatches() throws Exception {
        Path testFile = tempDir.resolve("edit.txt");
        java.nio.file.Files.writeString(testFile, "Hello Hello Hello");

        EditTool tool = new EditTool();
        ToolContext context = ToolContext.of(tempDir.toString(), "test-session");

        // Without replace_all, should fail for multiple matches
        Map<String, Object> args = Map.of(
            "file_path", testFile.toString(),
            "old_string", "Hello",
            "new_string", "Hi"
        );

        ToolResult result = tool.execute(args, context).join();

        assertFalse(result.success());
        assertTrue(result.error().contains("multiple") || result.error().contains("matches"));
    }

    @Test
    void testEditReplaceAll() throws Exception {
        Path testFile = tempDir.resolve("edit.txt");
        java.nio.file.Files.writeString(testFile, "Hello Hello Hello");

        EditTool tool = new EditTool();
        ToolContext context = ToolContext.of(tempDir.toString(), "test-session");

        Map<String, Object> args = Map.of(
            "file_path", testFile.toString(),
            "old_string", "Hello",
            "new_string", "Hi",
            "replace_all", true
        );

        ToolResult result = tool.execute(args, context).join();

        assertTrue(result.success());
        assertEquals("Hi Hi Hi", java.nio.file.Files.readString(testFile));
    }
}