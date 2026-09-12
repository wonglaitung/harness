package com.harness.memory;

import static org.junit.jupiter.api.Assertions.*;

import java.util.Map;

import org.junit.jupiter.api.Test;

/**
 * A4 tests for BlackboardItem provenance enforcement.
 */
class BlackboardItemProvenanceTest {

    @Test
    void createWithoutProvenance() {
        BlackboardItem item = BlackboardItem.create(
            "observation", Map.of("x", 1), "agent-a", 0.9f, "writer");
        assertNull(item.provenance());
    }

    @Test
    void withProvenanceSetsField() {
        BlackboardItem item = BlackboardItem.create(
            "decision", Map.of("y", 2), "agent-b", 1.0f, "harness");
        BlackboardItem withProv = item.withProvenance("file:report.pdf:page=3");
        assertEquals("file:report.pdf:page=3", withProv.provenance());
        assertEquals(item.id(), withProv.id());
    }

    @Test
    void withIncrementedVersionPreservesProvenance() {
        BlackboardItem item = BlackboardItem.create(
            "decision", Map.of("z", 3), "agent-c", 0.8f, "harness");
        BlackboardItem withProv = item.withProvenance("db:accounts:row=42");
        BlackboardItem bumped = withProv.withIncrementedVersion();
        assertEquals("db:accounts:row=42", bumped.provenance());
        assertEquals(1, bumped.baseVersion());
    }

    @Test
    void withStatusPreservesProvenance() {
        BlackboardItem item = BlackboardItem.create(
            "decision", Map.of("a", 1), "agent-d", 1.0f, "harness");
        BlackboardItem withProv = item.withProvenance("api:ledger:txn=abc");
        BlackboardItem resolved = withProv.withStatus("resolved");
        assertEquals("api:ledger:txn=abc", resolved.provenance());
        assertEquals("resolved", resolved.status());
    }
}
