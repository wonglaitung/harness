package com.harness.memory;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

/**
 * Tests for MemoryScoringConfig.
 */
class MemoryScoringConfigTest {

    @Test
    void testDefaultConfig() {
        MemoryScoringConfig config = MemoryScoringConfig.defaults();

        assertEquals(0.05, config.decayLambda());
        assertEquals(0.3, config.minRetrievalStrength());
        assertEquals(2000, config.maxCoreMemoryTokens());
        assertFalse(config.enableLlmEvaluation());
        assertEquals(MemoryScoringConfig.ArchiveFallback.FILE, config.archiveFallback());
    }

    @Test
    void testBuilder() {
        MemoryScoringConfig config = MemoryScoringConfig.builder()
            .decayLambda(0.1)
            .minRetrievalStrength(0.2)
            .maxCoreMemoryTokens(3000)
            .enableLlmEvaluation(true)
            .archiveFallback(MemoryScoringConfig.ArchiveFallback.DELETE)
            .build();

        assertEquals(0.1, config.decayLambda());
        assertEquals(0.2, config.minRetrievalStrength());
        assertEquals(3000, config.maxCoreMemoryTokens());
        assertTrue(config.enableLlmEvaluation());
        assertEquals(MemoryScoringConfig.ArchiveFallback.DELETE, config.archiveFallback());
    }

    @Test
    void testArchiveFallbackValues() {
        assertEquals(3, MemoryScoringConfig.ArchiveFallback.values().length);
        assertSame(MemoryScoringConfig.ArchiveFallback.FILE,
            MemoryScoringConfig.ArchiveFallback.valueOf("FILE"));
        assertSame(MemoryScoringConfig.ArchiveFallback.DELETE,
            MemoryScoringConfig.ArchiveFallback.valueOf("DELETE"));
        assertSame(MemoryScoringConfig.ArchiveFallback.NONE,
            MemoryScoringConfig.ArchiveFallback.valueOf("NONE"));
    }
}