package com.harness.core;

import java.nio.file.Path;
import java.util.List;

/**
 * Configuration for self-verification hook.
 */
public class SelfVerificationConfig {

    private final List<String> testCommand;
    private final List<String> triggerTools;
    private final Path workingDirectory;
    private final double timeout;
    private final int maxRetries;
    private final boolean verifyOnChange;
    private final boolean skipIfNoTests;
    private final String testPattern;

    private SelfVerificationConfig(Builder builder) {
        this.testCommand = builder.testCommand;
        this.triggerTools = builder.triggerTools;
        this.workingDirectory = builder.workingDirectory;
        this.timeout = builder.timeout;
        this.maxRetries = builder.maxRetries;
        this.verifyOnChange = builder.verifyOnChange;
        this.skipIfNoTests = builder.skipIfNoTests;
        this.testPattern = builder.testPattern;
    }

    /**
     * Command to run tests.
     */
    public List<String> testCommand() { return testCommand; }

    /**
     * Tools that trigger verification.
     */
    public List<String> triggerTools() { return triggerTools; }

    /**
     * Working directory for tests.
     */
    public Path workingDirectory() { return workingDirectory; }

    /**
     * Timeout for test execution in seconds.
     */
    public double timeout() { return timeout; }

    /**
     * Maximum test retry attempts.
     */
    public int maxRetries() { return maxRetries; }

    /**
     * Whether to run tests on every code change.
     */
    public boolean verifyOnChange() { return verifyOnChange; }

    /**
     * Whether to skip verification if no tests exist.
     */
    public boolean skipIfNoTests() { return skipIfNoTests; }

    /**
     * Pattern to detect test files.
     */
    public String testPattern() { return testPattern; }

    /**
     * Create default configuration.
     */
    public static SelfVerificationConfig defaults() {
        return builder().build();
    }

    /**
     * Create builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private List<String> testCommand = List.of("mvn", "test", "-q");
        private List<String> triggerTools = List.of("write", "edit", "write_file", "edit_file");
        private Path workingDirectory = null;
        private double timeout = 60.0;
        private int maxRetries = 3;
        private boolean verifyOnChange = true;
        private boolean skipIfNoTests = true;
        private String testPattern = ".*Test\\.java$|.*Tests\\.java$";

        public Builder testCommand(List<String> v) { this.testCommand = v; return this; }
        public Builder testCommand(String... v) { this.testCommand = List.of(v); return this; }
        public Builder triggerTools(List<String> v) { this.triggerTools = v; return this; }
        public Builder workingDirectory(Path v) { this.workingDirectory = v; return this; }
        public Builder timeout(double v) { this.timeout = v; return this; }
        public Builder maxRetries(int v) { this.maxRetries = v; return this; }
        public Builder verifyOnChange(boolean v) { this.verifyOnChange = v; return this; }
        public Builder skipIfNoTests(boolean v) { this.skipIfNoTests = v; return this; }
        public Builder testPattern(String v) { this.testPattern = v; return this; }

        public SelfVerificationConfig build() {
            return new SelfVerificationConfig(this);
        }
    }
}
