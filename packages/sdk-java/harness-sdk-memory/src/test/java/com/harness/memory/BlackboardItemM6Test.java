package com.harness.memory;

import static org.junit.jupiter.api.Assertions.*;

import java.time.Instant;
import java.util.Map;
import java.util.List;

import org.junit.jupiter.api.Test;

/**
 * M6-H tests for BlackboardItem.
 */
class BlackboardItemM6Test {

    @Test
    void createGeneratesIdAndDefaults() {
        BlackboardItem item = BlackboardItem.create("decision",
            Map.of("key", "value"), "planner", 0.9f, "harness");
        assertNotNull(item.id());
        assertEquals("decision", item.type());
        assertEquals("planner", item.sourceAgent());
        assertEquals(0.9f, item.confidence(), 0.001f);
        assertEquals(0, item.baseVersion());
        assertEquals("active", item.status());
        assertEquals("harness", item.writerId());
        assertNull(item.effectiveWriter());
        assertNotNull(item.createdAt());
    }

    @Test
    void createWithTtl() {
        BlackboardItem item = BlackboardItem.create("observation",
            Map.of(), "observer", 0.8f, "harness", 3600);
        assertEquals(3600, item.ttlSeconds());
        assertFalse(item.isExpired());  // just created
    }

    @Test
    void isExpiredReturnsFalseWhenNoTtl() {
        BlackboardItem item = BlackboardItem.create("decision", Map.of(), "a", 0.5f, "w");
        assertFalse(item.isExpired());
    }

    @Test
    void withIncrementedVersionBumpsVersion() {
        BlackboardItem item = BlackboardItem.create("decision", Map.of(), "a", 0.5f, "w");
        BlackboardItem bumped = item.withIncrementedVersion();
        assertEquals(1, bumped.baseVersion());
        assertEquals(0, item.baseVersion());  // original unchanged
    }

    @Test
    void withStatusChangesStatus() {
        BlackboardItem item = BlackboardItem.create("decision", Map.of(), "a", 0.5f, "w");
        BlackboardItem resolved = item.withStatus("resolved");
        assertEquals("resolved", resolved.status());
        assertEquals("active", item.status());  // original unchanged
    }
}
