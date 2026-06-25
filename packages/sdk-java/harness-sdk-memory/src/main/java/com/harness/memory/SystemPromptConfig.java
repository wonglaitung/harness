package com.harness.memory;

import java.nio.file.Path;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Configuration for dynamic system prompt assembly.
 */
public record SystemPromptConfig(
    String basePrompt,
    Path agentsMdPath,
    Path memoryMdPath,
    Path projectRoot,
    boolean autoDiscover,
    Map<String, SystemPromptSource> customSources,
    String sectionSeparator
) {

    public SystemPromptConfig() {
        this("", null, null, null, true, new HashMap<>(), "\n\n---\n\n");
    }

    /**
     * Create default configuration.
     */
    public static SystemPromptConfig defaults() {
        return new SystemPromptConfig();
    }

    /**
     * Create builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String basePrompt = "";
        private Path agentsMdPath = null;
        private Path memoryMdPath = null;
        private Path projectRoot = null;
        private boolean autoDiscover = true;
        private Map<String, SystemPromptSource> customSources = new HashMap<>();
        private String sectionSeparator = "\n\n---\n\n";

        public Builder basePrompt(String value) {
            this.basePrompt = value;
            return this;
        }

        public Builder agentsMdPath(Path value) {
            this.agentsMdPath = value;
            return this;
        }

        public Builder memoryMdPath(Path value) {
            this.memoryMdPath = value;
            return this;
        }

        public Builder projectRoot(Path value) {
            this.projectRoot = value;
            return this;
        }

        public Builder autoDiscover(boolean value) {
            this.autoDiscover = value;
            return this;
        }

        public Builder addCustomSource(SystemPromptSource source) {
            this.customSources.put(source.name(), source);
            return this;
        }

        public Builder sectionSeparator(String value) {
            this.sectionSeparator = value;
            return this;
        }

        public SystemPromptConfig build() {
            return new SystemPromptConfig(
                basePrompt,
                agentsMdPath,
                memoryMdPath,
                projectRoot,
                autoDiscover,
                customSources,
                sectionSeparator
            );
        }
    }
}
