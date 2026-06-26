package com.harness.memory;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Builds system prompts from multiple sources.
 *
 * Supports loading system prompts from multiple sources:
 * - Base system prompt (from config)
 * - AGENTS.md file in project root (project-specific instructions)
 * - MEMORY.md file for persistent context
 * - Custom system prompt providers
 *
 * Priority order (highest first):
 * 1. Base system prompt
 * 2. Custom sources (sorted by priority)
 * 3. AGENTS.md (project instructions)
 * 4. MEMORY.md (persistent context)
 *
 * Example:
 * <pre>
 * SystemPromptBuilder builder = new SystemPromptBuilder(
 *     SystemPromptConfig.builder()
 *         .basePrompt("You are a helpful assistant.")
 *         .projectRoot(Path.of("/path/to/project"))
 *         .build()
 * );
 *
 * String fullPrompt = builder.build();
 * </pre>
 */
public class SystemPromptBuilder {

    private static final Logger logger = LoggerFactory.getLogger(SystemPromptBuilder.class);

    private final SystemPromptConfig config;
    private final List<SystemPromptSource> sources = new ArrayList<>();

    public SystemPromptBuilder() {
        this(SystemPromptConfig.defaults());
    }

    public SystemPromptBuilder(SystemPromptConfig config) {
        this.config = config;
        setupDefaultSources();
    }

    private void setupDefaultSources() {
        sources.clear();

        // Base prompt (highest priority)
        if (config.basePrompt() != null && !config.basePrompt().isEmpty()) {
            sources.add(new SystemPromptSource("base", 100, config.basePrompt(), null, false));
        }

        // AGENTS.md (project instructions)
        Path agentsPath = config.agentsMdPath();
        if (agentsPath == null && config.projectRoot() != null && config.autoDiscover()) {
            agentsPath = config.projectRoot().resolve("AGENTS.md");
        }
        if (agentsPath != null) {
            sources.add(new SystemPromptSource("AGENTS.md", 50, null, agentsPath, false));
        }

        // MEMORY.md (persistent context)
        Path memoryPath = config.memoryMdPath();
        if (memoryPath == null && config.projectRoot() != null && config.autoDiscover()) {
            memoryPath = config.projectRoot().resolve("MEMORY.md");
        }
        if (memoryPath != null) {
            sources.add(new SystemPromptSource("MEMORY.md", 40, null, memoryPath, false));
        }

        // Custom sources
        if (config.customSources() != null) {
            sources.addAll(config.customSources().values());
        }

        // Sort by priority (highest first)
        sources.sort(Comparator.comparingInt(SystemPromptSource::priority).reversed());
    }

    /**
     * Add a new source to the builder.
     */
    public void addSource(SystemPromptSource source) {
        sources.add(source);
        sources.sort(Comparator.comparingInt(SystemPromptSource::priority).reversed());
    }

    /**
     * Remove a source by name.
     */
    public boolean removeSource(String name) {
        return sources.removeIf(s -> s.name().equals(name));
    }

    /**
     * Build the full system prompt from all sources.
     */
    public String build() {
        List<String> sections = new ArrayList<>();

        for (SystemPromptSource source : sources) {
            try {
                String content = source.getContent();
                if (content != null && !content.isEmpty() && !content.isBlank()) {
                    sections.add(content);
                    logger.debug("Added system prompt section from '{}': {} chars", source.name(), content.length());
                }
            } catch (Exception e) {
                logger.warn("Error loading system prompt source '{}': {}", source.name(), e.getMessage());
                if (source.required()) {
                    throw new RuntimeException("Required system prompt source failed: " + source.name(), e);
                }
            }
        }

        return String.join(config.sectionSeparator(), sections);
    }

    /**
     * Get list of source names that have content.
     */
    public List<String> getAvailableSources() {
        List<String> available = new ArrayList<>();
        for (SystemPromptSource source : sources) {
            try {
                String content = source.getContent();
                if (content != null && !content.isEmpty() && !content.isBlank()) {
                    available.add(source.name());
                }
            } catch (Exception e) {
                // Skip unavailable sources
            }
        }
        return available;
    }

    /**
     * Get content from a specific source.
     */
    public String getSourceContent(String name) {
        for (SystemPromptSource source : sources) {
            if (source.name().equals(name)) {
                try {
                    return source.getContent();
                } catch (Exception e) {
                    return null;
                }
            }
        }
        return null;
    }
}
