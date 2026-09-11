package com.harness.memory;

import static org.junit.jupiter.api.Assertions.*;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.Map;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * M6 tests for FileStateStore (SQLite-backed shared state).
 */
class FileStateStoreM6Test {

    @TempDir
    Path tempDir;

    private FileStateStore store;
    private Path dbPath;

    @BeforeEach
    void setUp() {
        dbPath = tempDir.resolve("test-state.db");
        store = new FileStateStore(dbPath);
    }

    @AfterEach
    void tearDown() {
        if (store != null) {
            store.close();
        }
    }

    @Test
    void putAndGetBasic() {
        BlackboardItem item = BlackboardItem.create(
            "decision", Map.of("key", "value"), "planner", 0.9f, "harness");
        store.put(item);

        BlackboardItem retrieved = store.get(item.getId());
        assertNotNull(retrieved);
        assertEquals(item.getId(), retrieved.id());
        assertEquals("decision", retrieved.type());
        assertEquals("planner", retrieved.sourceAgent());
    }

    @Test
    void getExpiredReturnsNull() {
        BlackboardItem item = new BlackboardItem(
            "expired-item", "decision", Map.of("key", "value"),
            "planner", 0.9f, 0, -1, // ttlSeconds = -1 → expired
            ItemStatus.CONFIRMED, "harness", "harness", Instant.now().minusSeconds(3600));
        store.put(item);

        BlackboardItem retrieved = store.get(item.getId());
        assertNull(retrieved);
    }

    @Test
    void writeIfVersionCAS() {
        BlackboardItem item = BlackboardItem.create(
            "cas-test", Map.of("v", 1), "planner", 0.9f, "harness");
        store.put(item);

        // CAS should succeed with correct base version
        boolean ok = store.writeIfVersion(item.getId(), Map.of("v", 2), 0);
        assertTrue(ok);

        // CAS should fail with wrong base version
        boolean fail = store.writeIfVersion(item.getId(), Map.of("v", 3), 0);
        assertFalse(fail);

        // Verify final state
        BlackboardItem updated = store.get(item.getId());
        assertNotNull(updated);
        assertEquals(1, updated.baseVersion());
    }

    @Test
    void writeIfVersionAuthoritativeWithVerifier() {
        Predicate<BlackboardItem> verifier = item ->
            "harness".equals(item.writerId());

        FileStateStore verifiedStore = new FileStateStore(
            tempDir.resolve("verified.db"), false, verifier, null);
        try {
            BlackboardItem item = new BlackboardItem(
                "auth-cas", "authoritative", Map.of("v", 1),
                "planner", 0.9f, 0, 3600,
                ItemStatus.PROPOSED, "harness", "harness", Instant.now());
            verifiedStore.put(item);

            boolean ok = verifiedStore.writeIfVersion(item.getId(), Map.of("v", 2), 0);
            assertTrue(ok);
        } finally {
            verifiedStore.close();
        }
    }

    @Test
    void writeIfVersionAuthoritativeVerifierRejects() {
        Predicate<BlackboardItem> verifier = item -> false; // reject all

        FileStateStore rejectStore = new FileStateStore(
            tempDir.resolve("reject.db"), false, verifier, null);
        try {
            BlackboardItem item = new BlackboardItem(
                "auth-reject", "authoritative", Map.of("v", 1),
                "planner", 0.9f, 0, 3600,
                ItemStatus.PROPOSED, "rogue", "rogue", Instant.now());
            rejectStore.put(item);

            assertThrows(IllegalArgumentException.class, () ->
                rejectStore.writeIfVersion(item.getId(), Map.of("v", 2), 0));
        } finally {
            rejectStore.close();
        }
    }

    @Test
    void readVerifierRaiseRejects() {
        Predicate<BlackboardItem> readVerifier = item ->
            "harness".equals(item.sourceAgent());

        FileStateStore secureStore = new FileStateStore(
            tempDir.resolve("secure.db"), true, null, readVerifier);
        try {
            BlackboardItem item = new BlackboardItem(
                "forged", "decision", Map.of("key", "value"),
                "rogue", 0.9f, 0, 3600,
                ItemStatus.PROPOSED, "harness", "harness", Instant.now());
            secureStore.put(item);

            assertThrows(SecurityException.class, () ->
                secureStore.get("forged"));
        } finally {
            secureStore.close();
        }
    }

    @Test
    void readVerifierRaiseSilentlyDrops() {
        Predicate<BlackboardItem> readVerifier = item ->
            "harness".equals(item.sourceAgent());

        FileStateStore quietStore = new FileStateStore(
            tempDir.resolve("quiet.db"), false, null, readVerifier);
        try {
            BlackboardItem item = new BlackboardItem(
                "drop-me", "decision", Map.of("key", "value"),
                "rogue", 0.9f, 0, 3600,
                ItemStatus.PROPOSED, "harness", "harness", Instant.now());
            quietStore.put(item);

            BlackboardItem result = quietStore.get("drop-me");
            assertNull(result);
        } finally {
            quietStore.close();
        }
    }

    @Test
    void listItemsFiltersExpiredAndRejected() {
        BlackboardItem valid = BlackboardItem.create(
            "valid", Map.of("k", "v"), "planner", 0.9f, "harness");
        BlackboardItem expired = new BlackboardItem(
            "expired-list", "decision", Map.of("k", "v"),
            "planner", 0.9f, 0, -1,
            ItemStatus.PROPOSED, "harness", "harness", Instant.now());
        BlackboardItem rejected = new BlackboardItem(
            "rejected-list", "decision", Map.of("k", "v"),
            "rogue", 0.9f, 0, 3600,
            ItemStatus.PROPOSED, "harness", "harness", Instant.now());

        Predicate<BlackboardItem> verifier = item -> !"rogue".equals(item.sourceAgent());
        FileStateStore mixedStore = new FileStateStore(
            tempDir.resolve("mixed.db"), false, null, verifier);
        try {
            mixedStore.put(valid);
            mixedStore.put(expired);
            mixedStore.put(rejected);

            List<BlackboardItem> items = mixedStore.listItems();
            assertEquals(1, items.size());
            assertEquals("valid", items.get(0).id());
        } finally {
            mixedStore.close();
        }
    }

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
            "same-b", "decision", Map.of("verdict", "A"), // same content
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

    @Test
    void sizeUpdatesOnPut() {
        assertEquals(0, store.size());
        store.put(BlackboardItem.create("s1", Map.of("k", "v"), "planner", 0.9f, "harness"));
        assertEquals(1, store.size());
        store.put(BlackboardItem.create("s2", Map.of("k", "v"), "planner", 0.9f, "harness"));
        assertEquals(2, store.size());
    }

    @Test
    void closeAndReopen() {
        store.put(BlackboardItem.create("persist", Map.of("k", "v"), "planner", 0.9f, "harness"));
        store.close();

        // Reopen from same file
        FileStateStore reopened = new FileStateStore(dbPath);
        try {
            BlackboardItem item = reopened.get("persist");
            assertNotNull(item);
        } finally {
            reopened.close();
        }
    }
}
