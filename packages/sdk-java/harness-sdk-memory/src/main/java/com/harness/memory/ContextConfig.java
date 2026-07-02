package com.harness.memory;

import java.nio.file.Path;

/**
 * Configuration for context building.
 */
public class ContextConfig {

    private int maxTokens = 200000;
    private String systemPrompt = "";
    private int windowSize = 100;  // Max number of recent messages
    private double compressionThreshold = 0.9;  // Compress when usage > 90%
    private boolean enableCompression = true;
    private CompressionConfig compressionConfig = null;

    // Dynamic system prompt configuration
    private SystemPromptConfig systemPromptConfig = null;
    private Path projectRoot = null;
    private Path memoryMdPath = null;
    private boolean includeWorkingDirectory = true;

    public ContextConfig() {
    }

    public static ContextConfig defaults() {
        return new ContextConfig();
    }

    // Getters and setters

    public int maxTokens() { return maxTokens; }
    public void setMaxTokens(int value) { this.maxTokens = value; }

    public String systemPrompt() { return systemPrompt; }
    public void setSystemPrompt(String value) { this.systemPrompt = value; }

    public int windowSize() { return windowSize; }
    public void setWindowSize(int value) { this.windowSize = value; }

    public double compressionThreshold() { return compressionThreshold; }
    public void setCompressionThreshold(double value) { this.compressionThreshold = value; }

    public boolean enableCompression() { return enableCompression; }
    public void setEnableCompression(boolean value) { this.enableCompression = value; }

    public CompressionConfig compressionConfig() { return compressionConfig; }
    public void setCompressionConfig(CompressionConfig value) { this.compressionConfig = value; }

    public SystemPromptConfig systemPromptConfig() { return systemPromptConfig; }
    public void setSystemPromptConfig(SystemPromptConfig value) { this.systemPromptConfig = value; }

    public Path projectRoot() { return projectRoot; }
    public void setProjectRoot(Path value) { this.projectRoot = value; }

    public Path memoryMdPath() { return memoryMdPath; }
    public void setMemoryMdPath(Path value) { this.memoryMdPath = value; }

    public boolean includeWorkingDirectory() { return includeWorkingDirectory; }
    public void setIncludeWorkingDirectory(boolean value) { this.includeWorkingDirectory = value; }

    /**
     * Create builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private final ContextConfig config = new ContextConfig();

        public Builder maxTokens(int value) {
            config.setMaxTokens(value);
            return this;
        }

        public Builder systemPrompt(String value) {
            config.setSystemPrompt(value);
            return this;
        }

        public Builder windowSize(int value) {
            config.setWindowSize(value);
            return this;
        }

        public Builder compressionThreshold(double value) {
            config.setCompressionThreshold(value);
            return this;
        }

        public Builder enableCompression(boolean value) {
            config.setEnableCompression(value);
            return this;
        }

        public Builder compressionConfig(CompressionConfig value) {
            config.setCompressionConfig(value);
            return this;
        }

        public Builder systemPromptConfig(SystemPromptConfig value) {
            config.setSystemPromptConfig(value);
            return this;
        }

        public Builder projectRoot(Path value) {
            config.setProjectRoot(value);
            return this;
        }

        public Builder memoryMdPath(Path value) {
            config.setMemoryMdPath(value);
            return this;
        }

        public Builder includeWorkingDirectory(boolean value) {
            config.setIncludeWorkingDirectory(value);
            return this;
        }

        public ContextConfig build() {
            return config;
        }
    }
}