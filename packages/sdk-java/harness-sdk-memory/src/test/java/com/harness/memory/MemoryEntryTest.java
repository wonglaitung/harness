package com.harness.memory;

import static org.junit.jupiter.api.Assertions.*;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Map;

import org.junit.jupiter.api.Test;

/**
 * Tests for MemoryEntry - Retrieval Strength calculation.
 */
class MemoryEntryTest {

    @Test
    void testBasicCreation() {
        MemoryEntry entry = new MemoryEntry(MemoryCategory.KEY_DECISIONS, "Test content");

        assertEquals(MemoryCategory.KEY_DECISIONS, entry.category());
        assertEquals("Test content", entry.content());
        assertEquals(MemorySource.AGENT_OBSERVATION, entry.source());
        assertEquals(1.0, entry.importance());
        assertEquals(0, entry.accessCount());
    }

    @Test
    void testRetrievalStrengthNewEntry() {
        // New entry (0 days idle, 0 access) should have strength ~1.0
        MemoryEntry entry = new MemoryEntry(MemoryCategory.USER_PROFILE, "Test");

        double strength = entry.calculateRetrievalStrength(0.05, 0.3);

        // timeDecay = 0.3 + 0.7 * exp(0) = 1.0
        // accessBonus = 1 + 0.5 * log(1) = 1.0
        // strength = 1.0 * 1.0 = 1.0
        assertEquals(1.0, strength, 0.01);
    }

    @Test
    void testRetrievalStrengthWithAccess() {
        // Entry with 5 accesses should have higher strength
        MemoryEntry entry = MemoryEntry.builder()
            .category(MemoryCategory.USER_PROFILE)
            .content("Test")
            .accessCount(5)
            .build();

        double strength = entry.calculateRetrievalStrength(0.05, 0.3);

        // timeDecay = 1.0 (new entry)
        // accessBonus = 1 + 0.5 * log(6) = 1 + 0.5 * 1.79 = 1.89
        // strength > 1.0
        assertTrue(strength > 1.0);
        assertTrue(strength < 2.5); // bounded
    }

    @Test
    void testRetrievalStrengthDecay() {
        // Entry 10 days old should have lower strength
        Instant oldTime = Instant.now().minus(10, ChronoUnit.DAYS);
        MemoryEntry entry = MemoryEntry.builder()
            .category(MemoryCategory.USER_PROFILE)
            .content("Test")
            .createdAt(oldTime)
            .build();

        double strength = entry.calculateRetrievalStrength(0.05, 0.3);

        // timeDecay = 0.3 + 0.7 * exp(-0.05 * 10) = 0.3 + 0.7 * 0.606 = 0.72
        // accessBonus = 1.0
        // strength ~ 0.72
        assertTrue(strength < 1.0);
        assertTrue(strength >= 0.3); // never below minimum
    }

    @Test
    void testRetrievalStrengthNeverBelowMinimum() {
        // Very old entry (365 days) should still have min strength
        Instant oldTime = Instant.now().minus(365, ChronoUnit.DAYS);
        MemoryEntry entry = MemoryEntry.builder()
            .category(MemoryCategory.USER_PROFILE)
            .content("Test")
            .createdAt(oldTime)
            .build();

        double strength = entry.calculateRetrievalStrength(0.05, 0.3);

        // Should never go below minStrength (0.3)
        assertTrue(strength >= 0.3);
    }

    @Test
    void testTouchUpdatesAccessInfo() {
        MemoryEntry entry = new MemoryEntry(MemoryCategory.USER_PROFILE, "Test");
        MemoryEntry touched = entry.touch();

        assertEquals(entry.category(), touched.category());
        assertEquals(entry.content(), touched.content());
        assertEquals(1, touched.accessCount());
        assertNotNull(touched.lastAccessed());
        assertTrue(touched.lastAccessed().isAfter(entry.createdAt()));
    }

    @Test
    void testWithImportance() {
        MemoryEntry entry = new MemoryEntry(MemoryCategory.USER_PROFILE, "Test");
        MemoryEntry updated = entry.withImportance(0.5);

        assertEquals(0.5, updated.importance());
        assertEquals(entry.content(), updated.content());
    }

    @Test
    void testToMarkdownLineBasic() {
        MemoryEntry entry = new MemoryEntry(MemoryCategory.USER_PROFILE, "Test content");

        String line = entry.toMarkdownLine();

        assertEquals("- Test content", line);
    }

    @Test
    void testToMarkdownLineKeyDecision() {
        MemoryEntry entry = new MemoryEntry(MemoryCategory.KEY_DECISIONS, "Important decision");

        String line = entry.toMarkdownLine();

        // Should have date prefix
        assertTrue(line.startsWith("- "));
        assertTrue(line.contains(": Important decision"));
        assertTrue(line.matches("- \\d{4}-\\d{2}-\\d{2}: Important decision"));
    }

    @Test
    void testToMarkdownLineWithMetadata() {
        MemoryEntry entry = MemoryEntry.builder()
            .category(MemoryCategory.USER_PROFILE)
            .content("Test")
            .importance(0.8)
            .accessCount(3)
            .build();

        String line = entry.toMarkdownLine();

        // Should have HTML comment with metadata
        assertTrue(line.contains("<!--"));
        assertTrue(line.contains("importance=0.80"));
        assertTrue(line.contains("accesses=3"));
    }

    @Test
    void testBuilder() {
        Instant customTime = Instant.now().minus(5, ChronoUnit.DAYS);
        MemoryEntry entry = MemoryEntry.builder()
            .category(MemoryCategory.LEARNED_PATTERNS)
            .content("Custom content")
            .source(MemorySource.USER_INPUT)
            .createdAt(customTime)
            .importance(0.7)
            .accessCount(10)
            .lastAccessed(Instant.now())
            .metadata(Map.of("key", "value"))
            .build();

        assertEquals(MemoryCategory.LEARNED_PATTERNS, entry.category());
        assertEquals("Custom content", entry.content());
        assertEquals(MemorySource.USER_INPUT, entry.source());
        assertEquals(customTime, entry.createdAt());
        assertEquals(0.7, entry.importance());
        assertEquals(10, entry.accessCount());
        assertNotNull(entry.lastAccessed());
    }
}