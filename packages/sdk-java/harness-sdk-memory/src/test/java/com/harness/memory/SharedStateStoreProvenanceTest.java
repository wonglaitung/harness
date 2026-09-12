package com.harness.memory;

import static org.junit.jupiter.api.Assertions.*;

import java.util.Map;

import org.junit.jupiter.api.Test;

/**
 * A4 tests for SharedStateStore provenance enforcement on AUTHORITATIVE writes.
 */
class SharedStateStoreProvenanceTest {

    @Test
    void additiveWriteWithoutProvenanceAllowed() {
        SharedStateStore store = new SharedStateStore(false);
        BlackboardItem item = BlackboardItem.create(
            "observation", Map.of("x", 1), "agent-a", 0.5f, "writer");
        // ADDITIVE writes may omit provenance — observer/proposal role
        assertDoesNotThrow(() -> store.put(item));
    }

    @Test
    void authoritativeWriteWithoutProvenanceRejected() {
        SharedStateStore store = new SharedStateStore(false);
        BlackboardItem item = new BlackboardItem(
            "item-1", "decision", Map.of("y", 2), "agent-b",
            1.0f, 0, 0, "active", "harness", null,
            null,  // No provenance!
            java.time.Instant.now()
        );
        // AUTHORITATIVE without provenance must fail
        assertThrows(IllegalArgumentException.class, () -> store.put(item));
    }

    @Test
    void authoritativeWriteWithProvenanceAllowed() {
        SharedStateStore store = new SharedStateStore(false);
        BlackboardItem item = new BlackboardItem(
            "item-2", "decision", Map.of("z", 3), "agent-c",
            1.0f, 0, 0, "active", "harness", null,
            "file:report.pdf:page=3",  // Has provenance
            java.time.Instant.now()
        );
        assertDoesNotThrow(() -> store.put(item));
    }

    @Test
    void getReturnsStoredItem() {
        SharedStateStore store = new SharedStateStore(false);
        BlackboardItem item = new BlackboardItem(
            "item-3", "observation", Map.of("a", 1), "agent-d",
            0.8f, 0, 0, "active", "writer", null,
            "db:test:row=1",
            java.time.Instant.now()
        );
        store.put(item);
        BlackboardItem got = store.get("item-3");
        assertNotNull(got);
        assertEquals("db:test:row=1", got.provenance());
    }
}
