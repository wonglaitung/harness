package com.harness.security;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class SandboxExecutorTest {

    @Test
    void testBlockedCommand() {
        SandboxExecutor executor = new SandboxExecutor();

        // Should block dangerous commands
        assertFalse(executor.isCommandAllowed("rm -rf /"));
        assertFalse(executor.isCommandAllowed("sudo rm"));
        assertFalse(executor.isCommandAllowed("chmod -R 777"));
    }

    @Test
    void testAllowedCommand() {
        SandboxExecutor executor = new SandboxExecutor();

        // Should allow safe commands
        assertTrue(executor.isCommandAllowed("ls -la"));
        assertTrue(executor.isCommandAllowed("echo hello"));
        assertTrue(executor.isCommandAllowed("cat file.txt"));
    }

    @Test
    void testSandboxResult() {
        SandboxResult success = SandboxResult.success("output", "", 0);
        assertTrue(success.success());
        assertEquals(0, success.exitCode());

        SandboxResult failure = SandboxResult.failure("error message");
        assertFalse(failure.success());
        assertEquals("error message", failure.error());

        SandboxResult timeout = SandboxResult.timeout(30.0);
        assertFalse(timeout.success());
        assertTrue(timeout.error().contains("Timeout"));
    }
}