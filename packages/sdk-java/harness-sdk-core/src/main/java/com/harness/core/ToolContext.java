package com.harness.core;

import java.util.Map;

/**
 * Tool execution context.
 */
public record ToolContext(
    String sessionId,
    String workingDirectory,
    int iteration,
    Map<String, Object> metadata
) {

    public static final String DEFAULT_WORKING_DIR = System.getProperty("user.dir");

    public ToolContext(String sessionId) {
        this(sessionId, DEFAULT_WORKING_DIR, 0, Map.of());
    }

    /**
     * Builder for ToolContext.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String sessionId;
        private String workingDirectory = DEFAULT_WORKING_DIR;
        private int iteration = 0;
        private Map<String, Object> metadata = Map.of();

        public Builder sessionId(String sessionId) {
            this.sessionId = sessionId;
            return this;
        }

        public Builder workingDirectory(String workingDirectory) {
            this.workingDirectory = workingDirectory;
            return this;
        }

        public Builder iteration(int iteration) {
            this.iteration = iteration;
            return this;
        }

        public Builder metadata(Map<String, Object> metadata) {
            this.metadata = metadata;
            return this;
        }

        public ToolContext build() {
            return new ToolContext(sessionId, workingDirectory, iteration, metadata);
        }
    }
}