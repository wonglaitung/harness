package com.harness.core;

import java.nio.file.Path;
import java.util.List;

/**
 * Configuration for a sub-agent.
 */
public record SubAgentConfig(
    String name,
    String task,
    List<String> tools,
    int maxIterations,
    boolean inheritContext,
    String reportFormat,
    String systemPrompt,
    Path workingDirectory,
    double timeout
) {

    public SubAgentConfig(String name, String task) {
        this(name, task, null, 20, false, "summary", null, null, 0.0);
    }

    /**
     * Create builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String name;
        private String task;
        private List<String> tools = null;
        private int maxIterations = 20;
        private boolean inheritContext = false;
        private String reportFormat = "summary";
        private String systemPrompt = null;
        private Path workingDirectory = null;
        private double timeout = 0.0;

        public Builder name(String name) {
            this.name = name;
            return this;
        }

        public Builder task(String task) {
            this.task = task;
            return this;
        }

        public Builder tools(List<String> tools) {
            this.tools = tools;
            return this;
        }

        public Builder maxIterations(int maxIterations) {
            this.maxIterations = maxIterations;
            return this;
        }

        public Builder inheritContext(boolean inheritContext) {
            this.inheritContext = inheritContext;
            return this;
        }

        public Builder reportFormat(String reportFormat) {
            this.reportFormat = reportFormat;
            return this;
        }

        public Builder systemPrompt(String systemPrompt) {
            this.systemPrompt = systemPrompt;
            return this;
        }

        public Builder workingDirectory(Path workingDirectory) {
            this.workingDirectory = workingDirectory;
            return this;
        }

        public Builder timeout(double timeout) {
            this.timeout = timeout;
            return this;
        }

        public SubAgentConfig build() {
            return new SubAgentConfig(
                name, task, tools, maxIterations,
                inheritContext, reportFormat, systemPrompt,
                workingDirectory, timeout
            );
        }
    }
}
