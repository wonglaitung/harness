package com.harness.memory;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.function.Supplier;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * A source for system prompt content.
 */
public class SystemPromptSource {

    private static final Logger logger = LoggerFactory.getLogger(SystemPromptSource.class);

    private final String name;
    private final int priority;
    private final String content;
    private final Path filePath;
    private final boolean required;
    private final Supplier<String> contentSupplier;

    public SystemPromptSource(String name, int priority, String content, Path filePath, boolean required) {
        this.name = name;
        this.priority = priority;
        this.content = content;
        this.filePath = filePath;
        this.required = required;
        this.contentSupplier = null;
    }

    public SystemPromptSource(String name, int priority, Supplier<String> contentSupplier, boolean required) {
        this.name = name;
        this.priority = priority;
        this.content = null;
        this.filePath = null;
        this.required = required;
        this.contentSupplier = contentSupplier;
    }

    /**
     * Get the content from this source.
     */
    public String getContent() {
        if (contentSupplier != null) {
            return contentSupplier.get();
        }

        if (content != null) {
            return content;
        }

        if (filePath != null) {
            if (Files.exists(filePath)) {
                try {
                    String fileContent = Files.readString(filePath);
                    logger.debug("Loaded system prompt from '{}' ({}): {} chars", name, filePath, fileContent.length());
                    return fileContent;
                } catch (Exception e) {
                    if (required) {
                        throw new RuntimeException("Failed to read required file: " + filePath, e);
                    }
                    logger.debug("System prompt file not found for '{}': {}", name, filePath);
                    return "";
                }
            } else {
                if (required) {
                    throw new RuntimeException("Required system prompt file not found: " + filePath);
                }
                logger.debug("System prompt file not found for '{}': {}", name, filePath);
                return "";
            }
        }

        return "";
    }

    // Getters
    public String name() { return name; }
    public int priority() { return priority; }
    public Path filePath() { return filePath; }
    public boolean required() { return required; }
}
