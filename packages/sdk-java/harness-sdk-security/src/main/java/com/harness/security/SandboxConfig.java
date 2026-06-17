package com.harness.security;

/**
 * Sandbox configuration.
 *
 * Provides basic isolation settings.
 */
public record SandboxConfig(
    java.util.Set<String> allowedCommands,
    java.util.List<String> blockedPatterns,
    double maxExecutionTime,
    int maxOutputSize,
    java.util.Set<String> allowedEnvVars
) {

    /**
     * Default maximum execution time (30 seconds).
     */
    public static final double DEFAULT_MAX_EXECUTION_TIME = 30.0;

    /**
     * Default maximum output size (1MB).
     */
    public static final int DEFAULT_MAX_OUTPUT_SIZE = 1_000_000;

    /**
     * Create default configuration.
     */
    public static SandboxConfig defaultConfig() {
        return new SandboxConfig(
            null,
            LightweightSandbox.DEFAULT_BLOCKED_PATTERNS,
            DEFAULT_MAX_EXECUTION_TIME,
            DEFAULT_MAX_OUTPUT_SIZE,
            null
        );
    }

    /**
     * Create configuration with custom timeout.
     */
    public static SandboxConfig withTimeout(double timeout) {
        return new SandboxConfig(
            null,
            LightweightSandbox.DEFAULT_BLOCKED_PATTERNS,
            timeout,
            DEFAULT_MAX_OUTPUT_SIZE,
            null
        );
    }
}