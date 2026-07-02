package com.harness.core;

/**
 * Configuration for agent loop.
 *
 * @param maxIterations Maximum number of iterations (LLM calls).
 *                      - Simple tasks (read files, answer questions): 2-3
 *                      - Medium tasks (code analysis, multi-step reasoning): 5-7
 *                      - Complex tasks (code generation, research): 10-15
 *                      Default is 10 (industry standard: OpenAI Agents SDK, LangChain).
 * @param timeoutPerTool Timeout in seconds for each tool execution.
 * @param enableParallelTools Whether to execute tools in parallel when possible.
 * @param retryOnError Number of retries on LLM API errors.
 * @param enableProgress Whether to emit progress events.
 * @param enableCircuitBreaker Whether to enable circuit breaker for tool failures.
 * @param enableCostControl Whether to enable token/cost tracking.
 * @param workingDirectory Working directory for tool execution.
 * @param maxStuckFeedbacks Maximum stuck feedback injection attempts.
 * @param stuckMinIterations Minimum iterations before stuck detection.
 * @param stuckConsecutiveFailures Consecutive failures to trigger stuck detection.
 * @param memoryMdPath Path to MEMORY.md for UpdateCoreMemoryTool (null = use ~/.harness/).
 * @param toolResultRole Role for tool result messages: "tool" (native) or "user" (compatibility mode).
 * @param contextWindow Maximum context window size in tokens (default: 200000).
 * @param sessionWindow Maximum number of messages to keep in session sliding window.
 * @param enableCompression Whether to enable automatic context compression.
 * @param systemPrompt Base system prompt for the agent.
 */
public record LoopConfig(
    int maxIterations,
    long timeoutPerTool,
    boolean enableParallelTools,
    int retryOnError,
    boolean enableProgress,
    boolean enableCircuitBreaker,
    boolean enableCostControl,
    String workingDirectory,
    int maxStuckFeedbacks,
    int stuckMinIterations,
    int stuckConsecutiveFailures,
    String memoryMdPath,
    String toolResultRole,
    int contextWindow,
    int sessionWindow,
    boolean enableCompression,
    String systemPrompt
) {

    public static final int DEFAULT_MAX_ITERATIONS = 10;
    public static final long DEFAULT_TIMEOUT_PER_TOOL = 30_000L; // 30 seconds in millis
    public static final int DEFAULT_CONTEXT_WINDOW = 200_000;
    public static final int DEFAULT_SESSION_WINDOW = 100;

    public LoopConfig() {
        this(DEFAULT_MAX_ITERATIONS, DEFAULT_TIMEOUT_PER_TOOL, true, 3, true, true, true,
             System.getProperty("user.dir"), 2, 3, 3, null, "tool",
             DEFAULT_CONTEXT_WINDOW, DEFAULT_SESSION_WINDOW, true, "");
    }

    /**
     * Create default configuration.
     */
    public static LoopConfig defaults() {
        return new LoopConfig();
    }

    /**
     * Create builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private int maxIterations = DEFAULT_MAX_ITERATIONS;
        private long timeoutPerTool = DEFAULT_TIMEOUT_PER_TOOL;
        private boolean enableParallelTools = true;
        private int retryOnError = 3;
        private boolean enableProgress = true;
        private boolean enableCircuitBreaker = true;
        private boolean enableCostControl = true;
        private String workingDirectory = System.getProperty("user.dir");
        private int maxStuckFeedbacks = 2;
        private int stuckMinIterations = 3;
        private int stuckConsecutiveFailures = 3;
        private String memoryMdPath = null;
        private String toolResultRole = "tool";
        private int contextWindow = DEFAULT_CONTEXT_WINDOW;
        private int sessionWindow = DEFAULT_SESSION_WINDOW;
        private boolean enableCompression = true;
        private String systemPrompt = "";

        public Builder maxIterations(int maxIterations) {
            this.maxIterations = maxIterations;
            return this;
        }

        public Builder timeoutPerTool(long timeoutPerTool) {
            this.timeoutPerTool = timeoutPerTool;
            return this;
        }

        public Builder enableParallelTools(boolean enableParallelTools) {
            this.enableParallelTools = enableParallelTools;
            return this;
        }

        public Builder retryOnError(int retryOnError) {
            this.retryOnError = retryOnError;
            return this;
        }

        public Builder enableProgress(boolean enableProgress) {
            this.enableProgress = enableProgress;
            return this;
        }

        public Builder enableCircuitBreaker(boolean enableCircuitBreaker) {
            this.enableCircuitBreaker = enableCircuitBreaker;
            return this;
        }

        public Builder enableCostControl(boolean enableCostControl) {
            this.enableCostControl = enableCostControl;
            return this;
        }

        public Builder workingDirectory(String workingDirectory) {
            this.workingDirectory = workingDirectory;
            return this;
        }

        public Builder maxStuckFeedbacks(int maxStuckFeedbacks) {
            this.maxStuckFeedbacks = maxStuckFeedbacks;
            return this;
        }

        public Builder stuckMinIterations(int stuckMinIterations) {
            this.stuckMinIterations = stuckMinIterations;
            return this;
        }

        public Builder stuckConsecutiveFailures(int stuckConsecutiveFailures) {
            this.stuckConsecutiveFailures = stuckConsecutiveFailures;
            return this;
        }

        public Builder memoryMdPath(String memoryMdPath) {
            this.memoryMdPath = memoryMdPath;
            return this;
        }

        public Builder toolResultRole(String toolResultRole) {
            this.toolResultRole = toolResultRole;
            return this;
        }

        public Builder contextWindow(int contextWindow) {
            this.contextWindow = contextWindow;
            return this;
        }

        public Builder sessionWindow(int sessionWindow) {
            this.sessionWindow = sessionWindow;
            return this;
        }

        public Builder enableCompression(boolean enableCompression) {
            this.enableCompression = enableCompression;
            return this;
        }

        public Builder systemPrompt(String systemPrompt) {
            this.systemPrompt = systemPrompt;
            return this;
        }

        public LoopConfig build() {
            return new LoopConfig(
                maxIterations, timeoutPerTool, enableParallelTools, retryOnError,
                enableProgress, enableCircuitBreaker, enableCostControl, workingDirectory,
                maxStuckFeedbacks, stuckMinIterations, stuckConsecutiveFailures, memoryMdPath,
                toolResultRole, contextWindow, sessionWindow, enableCompression, systemPrompt
            );
        }
    }
}