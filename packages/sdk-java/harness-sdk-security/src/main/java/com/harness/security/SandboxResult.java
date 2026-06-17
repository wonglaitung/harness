package com.harness.security;

/**
 * Result of sandbox execution.
 */
public record SandboxResult(
    boolean success,
    String stdout,
    String stderr,
    int exitCode,
    String error
) {

    /**
     * Create a successful result.
     */
    public static SandboxResult success(String stdout, String stderr, int exitCode) {
        return new SandboxResult(true, stdout, stderr, exitCode, null);
    }

    /**
     * Create a failed result.
     */
    public static SandboxResult failure(String error) {
        return new SandboxResult(false, "", "", -1, error);
    }

    /**
     * Create a failed result with output.
     */
    public static SandboxResult failure(String stdout, String stderr, int exitCode) {
        return new SandboxResult(false, stdout, stderr, exitCode, null);
    }

    /**
     * Create a timeout result.
     */
    public static SandboxResult timeout(double seconds) {
        return new SandboxResult(false, "", "", -1, "Timeout after " + seconds + "s");
    }
}