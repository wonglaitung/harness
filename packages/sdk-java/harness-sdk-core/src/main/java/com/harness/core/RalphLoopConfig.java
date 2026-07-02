package com.harness.core;

import java.nio.file.Path;
import java.util.function.Predicate;

/**
 * Configuration for Ralph Loop.
 *
 * Ralph Loop intercepts exit attempts when the agent claims completion
 * but the task is not actually done. It saves progress and reinjects
 * a continuation prompt in a clean context.
 *
 * @param maxLoops Maximum number of continuation loops (default: 5)
 * @param contextThreshold Context threshold for triggering (fraction of max_tokens, default: 0.6)
 * @param continuationPromptTemplate Custom continuation prompt template
 * @param taskCompleteCheck Custom function to check if task is complete (return true if complete)
 * @param progressDir Directory to save progress files
 */
public record RalphLoopConfig(
    int maxLoops,
    double contextThreshold,
    String continuationPromptTemplate,
    Predicate<String> taskCompleteCheck,
    Path progressDir
) {

    public RalphLoopConfig() {
        this(5, 0.6, getDefaultContinuationTemplate(), null, null);
    }

    /**
     * Create default configuration.
     */
    public static RalphLoopConfig defaults() {
        return new RalphLoopConfig();
    }

    /**
     * Create builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    private static String getDefaultContinuationTemplate() {
        return """
            [任务继续] 之前的上下文已达到限制，但任务尚未完成。

            请继续之前的工作。以下是最后一步的输出摘要：

            {previous_response}

            请继续执行，直到任务完全完成。""";
    }

    public static class Builder {
        private int maxLoops = 5;
        private double contextThreshold = 0.6;
        private String continuationPromptTemplate = getDefaultContinuationTemplate();
        private Predicate<String> taskCompleteCheck = null;
        private Path progressDir = null;

        public Builder maxLoops(int value) {
            this.maxLoops = value;
            return this;
        }

        public Builder contextThreshold(double value) {
            this.contextThreshold = value;
            return this;
        }

        public Builder continuationPromptTemplate(String value) {
            this.continuationPromptTemplate = value;
            return this;
        }

        /**
         * Set custom task complete check function.
         *
         * The function receives the LLM response content and should return:
         * - true if the task is complete
         * - false if the task is incomplete and should continue
         *
         * Example:
         * <pre>
         * RalphLoopConfig.builder()
         *     .taskCompleteCheck(response -> response.contains("TASK_COMPLETE"))
         *     .build()
         * </pre>
         */
        public Builder taskCompleteCheck(Predicate<String> value) {
            this.taskCompleteCheck = value;
            return this;
        }

        public Builder progressDir(Path value) {
            this.progressDir = value;
            return this;
        }

        public RalphLoopConfig build() {
            return new RalphLoopConfig(
                maxLoops,
                contextThreshold,
                continuationPromptTemplate,
                taskCompleteCheck,
                progressDir
            );
        }
    }
}
