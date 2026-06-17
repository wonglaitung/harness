package com.harness.memory;

import java.time.Instant;
import java.util.Map;

/**
 * Memory entry - a single memory record.
 */
public record MemoryEntry(
    MemoryCategory category,
    String content,
    MemorySource source,
    Instant createdAt,
    Map<String, Object> metadata
) {

    public MemoryEntry(MemoryCategory category, String content, MemorySource source) {
        this(category, content, source, Instant.now(), Map.of());
    }

    public MemoryEntry(MemoryCategory category, String content) {
        this(category, content, MemorySource.AGENT_OBSERVATION, Instant.now(), Map.of());
    }

    /**
     * Convert to markdown list item.
     */
    public String toMarkdownLine() {
        if (category == MemoryCategory.KEY_DECISIONS) {
            String dateStr = createdAt.toString().substring(0, 10); // YYYY-MM-DD
            return "- " + dateStr + ": " + content;
        }
        return "- " + content;
    }

    /**
     * Builder for MemoryEntry.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private MemoryCategory category = MemoryCategory.PROJECT_CONTEXT;
        private String content;
        private MemorySource source = MemorySource.AGENT_OBSERVATION;
        private Instant createdAt = Instant.now();
        private Map<String, Object> metadata = Map.of();

        public Builder category(MemoryCategory category) {
            this.category = category;
            return this;
        }

        public Builder content(String content) {
            this.content = content;
            return this;
        }

        public Builder source(MemorySource source) {
            this.source = source;
            return this;
        }

        public Builder createdAt(Instant createdAt) {
            this.createdAt = createdAt;
            return this;
        }

        public Builder metadata(Map<String, Object> metadata) {
            this.metadata = metadata;
            return this;
        }

        public MemoryEntry build() {
            return new MemoryEntry(category, content, source, createdAt, metadata);
        }
    }
}