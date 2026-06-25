package com.harness.core;

/**
 * Configuration for Ralph Loop.
 *
 * Ralph Loop intercepts exit attempts when the agent claims completion
 * but the task is not actually done. It saves progress and reinjects
 * a continuation prompt in a clean context.
 */
public record RalphLoopConfig(
    int maxLoops,
    double contextThreshold,
    String continuationPromptTemplate
) {

    public RalphLoopConfig() {
        this(5, 0.6, getDefaultContinuationTemplate());
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

        public RalphLoopConfig build() {
            return new RalphLoopConfig(maxLoops, contextThreshold, continuationPromptTemplate);
        }
    }
}
