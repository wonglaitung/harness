package com.harness.loop.types;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Objects;

/**
 * Configuration for tool-based goal verification.
 *
 * <p>Tool verification runs commands (tests, lint, type check) to verify
 * if a goal has been achieved. This provides objective, deterministic
 * verification compared to LLM-based verification.</p>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * // Python project verification
 * ToolVerificationConfig pythonConfig = ToolVerificationConfig.builder()
 *     .addCommand("pytest", "pytest", "tests/", "-v")
 *     .addCommand("mypy", "mypy", "src/")
 *     .addCommand("ruff", "ruff", "check", "src/")
 *     .build();
 *
 * // Java project verification
 * ToolVerificationConfig javaConfig = ToolVerificationConfig.builder()
 *     .addCommand("gradle test", "gradle", "test")
 *     .workingDirectory("./project")
 *     .timeoutSeconds(300)
 *     .build();
 *
 * // Combined with GoalConfig
 * GoalConfig config = GoalConfig.builder()
 *     .description("Fix all type errors")
 *     .verificationMethod(VerificationMethod.TOOL)
 *     .toolVerificationConfig(pythonConfig)
 *     .build();
 * }</pre>
 *
 * <h2>Verification Logic</h2>
 * <ul>
 *   <li>All commands must succeed (exit code 0) for verification to pass</li>
 *   <li>If any command fails, verification fails with details</li>
 *   <li>Commands are run in sequence, stopping on first failure</li>
 *   <li>Output is captured and included in reasoning</li>
 * </ul>
 */
public class ToolVerificationConfig {

    private final List<VerificationCommand> commands;
    private final String workingDirectory;
    private final int timeoutSeconds;
    private final boolean failFast;
    private final boolean continueOnWarning;

    private ToolVerificationConfig(Builder builder) {
        this.commands = new ArrayList<>(builder.commands);
        this.workingDirectory = builder.workingDirectory;
        this.timeoutSeconds = builder.timeoutSeconds;
        this.failFast = builder.failFast;
        this.continueOnWarning = builder.continueOnWarning;
    }

    /**
     * Get the verification commands.
     */
    public List<VerificationCommand> getCommands() {
        return new ArrayList<>(commands);
    }

    /**
     * Get the working directory for command execution.
     */
    public String getWorkingDirectory() {
        return workingDirectory;
    }

    /**
     * Get the timeout for each command in seconds.
     */
    public int getTimeoutSeconds() {
        return timeoutSeconds;
    }

    /**
     * Whether to stop on first command failure.
     */
    public boolean isFailFast() {
        return failFast;
    }

    /**
     * Whether to continue if command exits with warning (non-zero but acceptable).
     */
    public boolean isContinueOnWarning() {
        return continueOnWarning;
    }

    /**
     * Create a builder for ToolVerificationConfig.
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Builder for ToolVerificationConfig.
     */
    public static class Builder {
        private List<VerificationCommand> commands = new ArrayList<>();
        private String workingDirectory = ".";
        private int timeoutSeconds = 300;  // 5 minutes default
        private boolean failFast = true;
        private boolean continueOnWarning = false;

        /**
         * Add a verification command.
         *
         * @param name Human-readable name for the command
         * @param command Command and arguments
         * @return Builder
         */
        public Builder addCommand(String name, String... command) {
            this.commands.add(new VerificationCommand(name, Arrays.asList(command)));
            return this;
        }

        /**
         * Add a verification command with explicit arguments list.
         *
         * @param name Human-readable name for the command
         * @param command Command executable
         * @param args Command arguments
         * @return Builder
         */
        public Builder addCommand(String name, String command, List<String> args) {
            List<String> fullCommand = new ArrayList<>();
            fullCommand.add(command);
            fullCommand.addAll(args);
            this.commands.add(new VerificationCommand(name, fullCommand));
            return this;
        }

        /**
         * Add a pre-defined verification command.
         *
         * @param command VerificationCommand object
         * @return Builder
         */
        public Builder addCommand(VerificationCommand command) {
            this.commands.add(command);
            return this;
        }

        /**
         * Set the working directory for command execution.
         *
         * @param workingDirectory Working directory path
         * @return Builder
         */
        public Builder workingDirectory(String workingDirectory) {
            this.workingDirectory = workingDirectory;
            return this;
        }

        /**
         * Set the timeout for each command.
         *
         * @param timeoutSeconds Timeout in seconds
         * @return Builder
         */
        public Builder timeoutSeconds(int timeoutSeconds) {
            this.timeoutSeconds = timeoutSeconds;
            return this;
        }

        /**
         * Set whether to stop on first failure.
         *
         * @param failFast True to stop on first failure
         * @return Builder
         */
        public Builder failFast(boolean failFast) {
            this.failFast = failFast;
            return this;
        }

        /**
         * Set whether to continue on warning-level exits.
         *
         * @param continueOnWarning True to continue on warnings
         * @return Builder
         */
        public Builder continueOnWarning(boolean continueOnWarning) {
            this.continueOnWarning = continueOnWarning;
            return this;
        }

        /**
         * Build the ToolVerificationConfig.
         */
        public ToolVerificationConfig build() {
            if (commands.isEmpty()) {
                throw new IllegalArgumentException("At least one verification command is required");
            }
            return new ToolVerificationConfig(this);
        }
    }

    /**
     * A single verification command.
     */
    public static class VerificationCommand {
        private final String name;
        private final List<String> command;

        public VerificationCommand(String name, List<String> command) {
            this.name = name;
            this.command = new ArrayList<>(command);
        }

        /**
         * Get the human-readable name.
         */
        public String getName() {
            return name;
        }

        /**
         * Get the command and arguments.
         */
        public List<String> getCommand() {
            return new ArrayList<>(command);
        }

        /**
         * Get the executable (first element of command).
         */
        public String getExecutable() {
            return command.isEmpty() ? "" : command.get(0);
        }

        /**
         * Get the arguments (all elements after the first).
         */
        public List<String> getArguments() {
            return command.size() > 1 ? new ArrayList<>(command.subList(1, command.size())) : new ArrayList<>();
        }

        @Override
        public boolean equals(Object o) {
            if (this == o) return true;
            if (o == null || getClass() != o.getClass()) return false;
            VerificationCommand that = (VerificationCommand) o;
            return Objects.equals(name, that.name) && Objects.equals(command, that.command);
        }

        @Override
        public int hashCode() {
            return Objects.hash(name, command);
        }

        @Override
        public String toString() {
            return "VerificationCommand{name='" + name + "', command=" + command + "}";
        }
    }

    // -------------------------------------------------------------------------
    // Pre-defined verification configurations
    // -------------------------------------------------------------------------

    /**
     * Create a Python project verification config (pytest + mypy + ruff).
     *
     * @return ToolVerificationConfig for Python projects
     */
    public static ToolVerificationConfig pythonDefaults() {
        return builder()
                .addCommand("pytest", "pytest", "tests/", "-v")
                .addCommand("mypy", "mypy", "src/")
                .addCommand("ruff", "ruff", "check", "src/")
                .build();
    }

    /**
     * Create a Python project verification config with custom test path.
     *
     * @param testPath Path to tests directory
     * @param srcPath Path to source directory
     * @return ToolVerificationConfig for Python projects
     */
    public static ToolVerificationConfig pythonProject(String testPath, String srcPath) {
        return builder()
                .addCommand("pytest", "pytest", testPath, "-v")
                .addCommand("mypy", "mypy", srcPath)
                .addCommand("ruff", "ruff", "check", srcPath)
                .build();
    }

    /**
     * Create a Java/Gradle project verification config.
     *
     * @return ToolVerificationConfig for Gradle projects
     */
    public static ToolVerificationConfig gradleDefaults() {
        return builder()
                .addCommand("gradle test", "gradle", "test")
                .addCommand("gradle check", "gradle", "check")
                .timeoutSeconds(600)  // Java tests can be slow
                .build();
    }

    /**
     * Create a Java/Maven project verification config.
     *
     * @return ToolVerificationConfig for Maven projects
     */
    public static ToolVerificationConfig mavenDefaults() {
        return builder()
                .addCommand("mvn test", "mvn", "test")
                .timeoutSeconds(600)
                .build();
    }

    /**
     * Create a Node.js/npm project verification config.
     *
     * @return ToolVerificationConfig for npm projects
     */
    public static ToolVerificationConfig npmDefaults() {
        return builder()
                .addCommand("npm test", "npm", "test")
                .addCommand("npm lint", "npm", "run", "lint")
                .build();
    }
}
