package com.harness.tools;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;

import java.nio.file.Path;
import java.util.Map;

import com.harness.core.ToolContext;
import com.harness.types.ToolResult;

class GrepToolTest {

    @TempDir
    Path tempDir;

    @Test
    void testGrepSearch() throws Exception {
        Path testFile = tempDir.resolve("search.txt");
        java.nio.file.Files.writeString(testFile, "Hello World\nJava Programming\nHello Java");

        GrepTool tool = new GrepTool();
        ToolContext context = ToolContext.of(tempDir.toString(), "test-session");

        Map<String, Object> args = Map.of("pattern", "Java");
        ToolResult result = tool.execute(args, context).join();

        assertTrue(result.success());
        assertTrue(result.content().contains("Java"));
        assertTrue(result.content().contains("Programming") || result.content().contains("2:"));
    }

    @Test
    void testGrepNoMatches() throws Exception {
        Path testFile = tempDir.resolve("search.txt");
        java.nio.file.Files.writeString(testFile, "Hello World");

        GrepTool tool = new GrepTool();
        ToolContext context = ToolContext.of(tempDir.toString(), "test-session");

        Map<String, Object> args = Map.of("pattern", "NotFound");
        ToolResult result = tool.execute(args, context).join();

        assertTrue(result.success());
        assertTrue(result.content().contains("No matches"));
    }

    @Test
    void testGrepIgnoreCase() throws Exception {
        Path testFile = tempDir.resolve("search.txt");
        java.nio.file.Files.writeString(testFile, "HELLO world");

        GrepTool tool = new GrepTool();
        ToolContext context = ToolContext.of(tempDir.toString(), "test-session");

        Map<String, Object> args = Map.of(
            "pattern", "hello",
            "ignore_case", true
        );
        ToolResult result = tool.execute(args, context).join();

        assertTrue(result.success());
        assertTrue(result.content().contains("HELLO"));
    }

    @Test
    void testGrepWithGlob() throws Exception {
        java.nio.file.Files.writeString(tempDir.resolve("test.java"), "public class Test");
        java.nio.file.Files.writeString(tempDir.resolve("test.txt"), "public function");

        GrepTool tool = new GrepTool();
        ToolContext context = ToolContext.of(tempDir.toString(), "test-session");

        Map<String, Object> args = Map.of(
            "pattern", "public",
            "glob", "*.java"
        );
        ToolResult result = tool.execute(args, context).join();

        assertTrue(result.success());
        assertTrue(result.content().contains("test.java"));
        assertFalse(result.content().contains("test.txt"));
    }
}