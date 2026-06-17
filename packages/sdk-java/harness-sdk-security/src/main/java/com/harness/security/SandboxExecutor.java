package com.harness.security;

import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Full sandbox executor with permission checking.
 *
 * Integrates with command blocking for comprehensive access control.
 */
public class SandboxExecutor {

    private static final Logger logger = LoggerFactory.getLogger(SandboxExecutor.class);

    /**
     * Default blocked commands.
     */
    public static final List<String> DEFAULT_BLOCKED_COMMANDS = List.of(
        "rm -rf /",
        "rm -rf ~",
        "sudo",
        "chmod -R 777",
        "mkfs",
        "dd if="
    );

    /**
     * Default maximum execution time (60 seconds).
     */
    public static final double DEFAULT_MAX_EXECUTION_TIME = 60.0;

    /**
     * Default maximum memory (512 MB).
     */
    public static final int DEFAULT_MAX_MEMORY_MB = 512;

    private final List<String> blockedCommands;
    private final double maxExecutionTime;
    private final int maxMemoryMb;

    /**
     * Create executor with default settings.
     */
    public SandboxExecutor() {
        this(DEFAULT_BLOCKED_COMMANDS, DEFAULT_MAX_EXECUTION_TIME, DEFAULT_MAX_MEMORY_MB);
    }

    /**
     * Create executor with custom settings.
     *
     * @param blockedCommands blocked command patterns
     * @param maxExecutionTime maximum execution time
     * @param maxMemoryMb maximum memory
     */
    public SandboxExecutor(List<String> blockedCommands, double maxExecutionTime, int maxMemoryMb) {
        this.blockedCommands = blockedCommands;
        this.maxExecutionTime = maxExecutionTime;
        this.maxMemoryMb = maxMemoryMb;
    }

    /**
     * Check if command is allowed.
     *
     * @param command command to check
     * @return true if command is allowed
     */
    public boolean isCommandAllowed(String command) {
        for (String blocked : blockedCommands) {
            if (command.contains(blocked)) {
                return false;
            }
        }
        return true;
    }

    /**
     * Execute command with permission check.
     *
     * @param command command to execute
     * @return CompletableFuture with SandboxResult
     */
    public CompletableFuture<SandboxResult> execute(String command) {
        return execute(command, null, null);
    }

    /**
     * Execute command with permission check.
     *
     * @param command command to execute
     * @param cwd working directory
     * @param env environment variables
     * @return CompletableFuture with SandboxResult
     */
    public CompletableFuture<SandboxResult> execute(String command, String cwd, Map<String, String> env) {
        if (!isCommandAllowed(command)) {
            logger.warn("Command not allowed: {}", command);
            return CompletableFuture.completedFuture(
                SandboxResult.failure("Command not allowed: contains blocked pattern")
            );
        }

        SandboxConfig config = new SandboxConfig(
            null,
            blockedCommands,
            maxExecutionTime,
            LightweightSandbox.DEFAULT_MAX_OUTPUT_SIZE,
            null
        );

        LightweightSandbox sandbox = new LightweightSandbox(config);
        return sandbox.execute(command, cwd, env, maxExecutionTime);
    }
}