package com.harness.memory;

import static org.junit.jupiter.api.Assertions.*;

import java.time.Instant;
import java.util.Map;
import java.util.List;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * M6-H tests for SharedStateStore.
 * Mirrors Python test_m6_hardening.py coverage.
 */
class SharedStateStoreM6Test {

    private SharedStateStore store;

    @BeforeEach
    void setUp() {
        store = new SharedStateStore();
    }

    // ---- Basic CRUD ----

    @Test
    void putAndGet() {
        BlackboardItem item = BlackboardItem.create("decision",
            Map.of("action", "approve"), "planner", 0.9f, "harness");
        store.put(item);
        BlackboardItem got = store.get(item.getId());
        assertNotNull(got);
        assertEquals(item.getId(), got.id());
    }

    @Test
    void getNonexistentReturnsNull() {
        assertNull(store.get("nonexistent"));
    }

    @Test
    void listItemsReturnsAll() {
        store.put(BlackboardItem.create("decision", Map.of(), "a", 0.5f, "w"));
        store.put(BlackboardItem.create("observation", Map.of(), "b", 0.5f, "w"));
        List<BlackboardItem> all = store.listItems();
        assertEquals(2, all.size());
    }

    // ---- CAS writeIfVersion ----

    @Test
    void writeIfVersionSucceedsOnMatch() {
        BlackboardItem item = BlackboardItem.create("decision",
            Map.of("v", "old"), "a", 0.5f, "w");
        store.put(item);
        boolean ok = store.writeIfVersion(item.getId(), Map.of("v", "new"), 0);
        assertTrue(ok);
        assertEquals(1, store.getVersion(item.getId()));
        assertEquals("new", store.get(item.getId()).content().get("v"));
    }

    @Test
    void writeIfVersionFailsOnMismatch() {
        BlackboardItem item = BlackboardItem.create("decision",
            Map.of("v", "old"), "a", 0.5f, "w");
        store.put(item);
        // Version is 0, but we pass 1
        boolean ok = store.writeIfVersion(item.getId(), Map.of("v", "new"), 1);
        assertFalse(ok);
        assertEquals(0, store.getVersion(item.getId()));  // unchanged
    }

    @Test
    void writeIfVersionThrowsOnMissing() {
        assertThrows(IllegalArgumentException.class,
            () -> store.writeIfVersion("nonexistent", Map.of(), 0));
    }

    // ---- readVerifierRaise ----

    @Test
    void readVerifierRaiseBlocksForbiddenItem() {
        SharedStateStore strictStore = new SharedStateStore(true,
            null,
            item -> false);  // readVerifier rejects everything

        strictStore.put(BlackboardItem.create("authoritative",
            Map.of(), "a", 0.9f, "harness"));

        assertThrows(SecurityException.class, () -> strictStore.get(
            strictStore.listItems().get(0).getId()));
    }

    @Test
    void readVerifierDropModeSilent() {
        SharedStateStore silentStore = new SharedStateStore(false,
            null,
            item -> false);  // readVerifier rejects everything

        silentStore.put(BlackboardItem.create("authoritative",
            Map.of(), "a", 0.9f, "harness"));

        // No exception, just returns null
        BlackboardItem got = silentStore.get(silentStore.listItems().get(0).getId());
        assertNull(got);
    }

    // ---- TTL expiry ----

    @Test
    void expiredItemNotReturned() {
        BlackboardItem item = new BlackboardItem(
            "id-1", "observation", Map.of(), "a", 0.5f,
            0, 1,  // ttlSeconds=1 (very short)
            "active", "w", null, Instant.now().minusSeconds(10));
        store.put(item);
        assertNull(store.get("id-1"));  // expired
    }

    // ---- size ----

    @Test
    void sizeTracksItems() {
        assertEquals(0, store.size());
        store.put(BlackboardItem.create("a", Map.of(), "x", 0.5f, "w"));
        assertEquals(1, store.size());
        store.put(BlackboardItem.create("b", Map.of(), "x", 0.5f, "w"));
        assertEquals(2, store.size());
    }

    // ---- Write verifier ----

    @Test
    void writeVerifierRejectsAuthoritative() {
        SharedStateStore verifiedStore = new SharedStateStore(false,
            item -> false,  // writeVerifier rejects
            null);

        assertThrows(IllegalArgumentException.class,
            () -> verifiedStore.put(BlackboardItem.create("authoritative",
                Map.of(), "a", 0.9f, "harness")));
    }

    @Test
    void writeVerifierAllowsAdditive() {
        SharedStateStore verifiedStore = new SharedStateStore(false,
            item -> false,  // writeVerifier rejects authoritative
            null);

        // Additive should pass (verifier only checks authoritative)
        assertDoesNotThrow(() -> verifiedStore.put(BlackboardItem.create("additive",
            Map.of(), "a", 0.5f, "harness")));
    }

    // ---- getConflicts ----

    @Test
    void getConflictsDetectsConflictingAuthoritative() {
        BlackboardItem itemA = new BlackboardItem(
            "conflict-a", "decision", Map.of("verdict", "A"),
            "planner", 0.9f, 0, 3600,
            ItemStatus.PROPOSED, "harness", "harness", Instant.now());
        BlackboardItem itemB = new BlackboardItem(
            "conflict-b", "decision", Map.of("verdict", "B"),
            "planner", 0.9f, 0, 3600,
            ItemStatus.PROPOSED, "harness", "harness", Instant.now());

        store.put(itemA);
        store.put(itemB);

        List<ConflictSet> conflicts = store.getConflicts();
        assertEquals(1, conflicts.size());
        ConflictSet cs = conflicts.get(0);
        assertEquals("decision", cs.key());
        assertTrue(cs.itemIds().contains("conflict-a"));
        assertTrue(cs.itemIds().contains("conflict-b"));
    }

    @Test
    void getConflictsNoConflictWhenSameContent() {
        BlackboardItem itemA = new BlackboardItem(
            "same-a", "decision", Map.of("verdict", "A"),
            "planner", 0.9f, 0, 3600,
            ItemStatus.PROPOSED, "harness", "harness", Instant.now());
        BlackboardItem itemB = new BlackboardItem(
            "same-b", "decision", Map.of("verdict", "A"),
            "planner", 0.9f, 0, 3600,
            ItemStatus.PROPOSED, "harness", "harness", Instant.now());

        store.put(itemA);
        store.put(itemB);

        List<ConflictSet> conflicts = store.getConflicts();
        assertTrue(conflicts.isEmpty());
    }

    @Test
    void getConflictsIgnoresAdditive() {
        BlackboardItem itemA = new BlackboardItem(
            "add-a", "observation", Map.of("data", "X"),
            "planner", 0.9f, 0, 3600,
            ItemStatus.PROPOSED, "harness", "harness", Instant.now());
        BlackboardItem itemB = new BlackboardItem(
            "add-b", "observation", Map.of("data", "Y"),
            "planner", 0.9f, 0, 3600,
            ItemStatus.PROPOSED, "harness", "harness", Instant.now());

        store.put(itemA);
        store.put(itemB);

        List<ConflictSet> conflicts = store.getConflicts();
        assertTrue(conflicts.isEmpty());
    }
}
