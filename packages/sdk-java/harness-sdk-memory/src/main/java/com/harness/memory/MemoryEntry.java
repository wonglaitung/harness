package com.harness.memory;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Map;

/**
 * Memory entry - a single memory record.
 *
 * Supports Retrieval Strength calculation based on Bjork's New Theory of Disuse:
 * - Storage Strength (importance): Used for archive decision
 * - Retrieval Strength: Time decay + access bonus, used for memory prioritization
 */
public record MemoryEntry(
    MemoryCategory category,
    String content,
    MemorySource source,
    Instant createdAt,
    Map<String, Object> metadata,
    double importance,           // Storage Strength (used for archive decision)
    Instant lastAccessed,        // Last access time
    int accessCount              // Access count
) {

    public MemoryEntry(MemoryCategory category, String content, MemorySource source) {
        this(category, content, source, Instant.now(), Map.of(), 1.0, null, 0);
    }

    public MemoryEntry(MemoryCategory category, String content) {
        this(category, content, MemorySource.AGENT_OBSERVATION, Instant.now(), Map.of(), 1.0, null, 0);
    }

    /**
     * Calculate Retrieval Strength (only for Retrieved Memory).
     *
     * Based on Bjork's New Theory of Disuse:
     * - Time decay: older memories decay but never below minStrength
     * - Access bonus: frequently accessed memories get bonus
     *
     * @param decayLambda Decay speed (higher = faster decay)
     * @param minStrength Minimum retrieval strength (floor)
     * @return Retrieval strength value (minStrength to ~2.5)
     */
    public double calculateRetrievalStrength(double decayLambda, double minStrength) {
        // Calculate days idle
        Instant accessTime = lastAccessed != null ? lastAccessed : createdAt;
        long daysIdle = ChronoUnit.DAYS.between(accessTime, Instant.now());

        // Time decay factor (never below minStrength)
        double timeDecay = minStrength + (1 - minStrength) * Math.exp(-decayLambda * daysIdle);

        // Access bonus factor
        double accessBonus = 1 + 0.5 * Math.log(1 + accessCount);

        return timeDecay * accessBonus;
    }

    /**
     * Calculate retrieval strength with default parameters.
     */
    public double calculateRetrievalStrength() {
        return calculateRetrievalStrength(0.05, 0.3);
    }

    /**
     * Create a new entry with updated access info.
     */
    public MemoryEntry touch() {
        return new MemoryEntry(
            category, content, source, createdAt, metadata,
            importance, Instant.now(), accessCount + 1
        );
    }

    /**
     * Create a new entry with updated importance.
     */
    public MemoryEntry withImportance(double newImportance) {
        return new MemoryEntry(
            category, content, source, createdAt, metadata,
            newImportance, lastAccessed, accessCount
        );
    }

    /**
     * Convert to markdown list item.
     */
    public String toMarkdownLine() {
        String base;
        if (category == MemoryCategory.KEY_DECISIONS) {
            String dateStr = createdAt.toString().substring(0, 10); // YYYY-MM-DD
            base = "- " + dateStr + ": " + content;
        } else {
            base = "- " + content;
        }

        // Add metadata as HTML comment if non-default
        if (importance != 1.0 || accessCount > 0) {
            return base + String.format(" <!-- importance=%.2f, accesses=%d -->", importance, accessCount);
        }

        return base;
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
        private double importance = 1.0;
        private Instant lastAccessed = null;
        private int accessCount = 0;

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

        public Builder importance(double importance) {
            this.importance = importance;
            return this;
        }

        public Builder lastAccessed(Instant lastAccessed) {
            this.lastAccessed = lastAccessed;
            return this;
        }

        public Builder accessCount(int accessCount) {
            this.accessCount = accessCount;
            return this;
        }

        public MemoryEntry build() {
            return new MemoryEntry(category, content, source, createdAt, metadata, importance, lastAccessed, accessCount);
        }
    }
}