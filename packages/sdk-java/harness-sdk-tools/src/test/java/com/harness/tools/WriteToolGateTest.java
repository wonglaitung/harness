package com.harness.tools;

import static org.junit.jupiter.api.Assertions.*;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Tests for WriteTool deterministic gate (B2).
 */
class WriteToolGateTest {

    private WriteTool tool;
    @TempDir Path tempDir;

    @BeforeEach
    void setUp() {
        tool = new WriteTool();
    }

    @Test
    void writeBlockedEtcPath() throws IOException {
        var args = java.util.Map.<String, Object>of(
            "file_path", "/etc/passwd",
            "content", "malicious"
        );
        var ctx = new com.harness.core.ToolContext("test-session", tempDir.toString());
        var result = tool.execute(args, ctx).join();
        assertFalse(result.success());
        assertTrue(result.error().contains("Deterministic gate rejected"));
        assertFalse(Files.exists(Path.of("/etc/passwd")));
    }

    @Test
    void writeBlockedRootPath() throws IOException {
        var args = java.util.Map.<String, Object>of(
            "file_path", "/root/.ssh/id_rsa",
            "content", "stolen key"
        );
        var ctx = new com.harness.core.ToolContext("test-session", tempDir.toString());
        var result = tool.execute(args, ctx).join();
        assertFalse(result.success());
        assertTrue(result.error().contains("Deterministic gate rejected"));
    }

    @Test
    void writeAllowedTempFile() throws IOException {
        Path target = tempDir.resolve("output.txt");
        var args = java.util.Map.<String, Object>of(
            "file_path", target.toString(),
            "content", "safe content"
        );
        var ctx = new com.harness.core.ToolContext("test-session", tempDir.toString());
        var result = tool.execute(args, ctx).join();
        assertTrue(result.success());
        assertEquals("safe content", Files.readString(target));
    }
}
