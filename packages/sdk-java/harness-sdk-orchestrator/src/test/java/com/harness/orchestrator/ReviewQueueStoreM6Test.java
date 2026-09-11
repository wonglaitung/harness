package com.harness.orchestrator;

import static org.junit.jupiter.api.Assertions.*;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import com.harness.memory.FileStateStore;
import com.harness.memory.StateStore;

/**
 * M6-G tests for ReviewQueue with store-backed persistence.
 */
class ReviewQueueStoreM6Test {

    @TempDir
    Path tempDir;

    private StateStore store;
    private ReviewQueue queue;

    @BeforeEach
    void setUp() {
        store = new FileStateStore(tempDir.resolve("review.db"));
        queue = new ReviewQueue(Set.of("human", "auditor:alice"), null, null, store, "review_queue");
    }

    @AfterEach
    void tearDown() {
        if (store instanceof FileStateStore fss) {
            fss.close();
        }
    }

    @Test
    void submitPersistsToStore() {
        ReviewItem item = ReviewItem.of("test content", "gate", List.of());
        String id = queue.submit(item);

        // Item should be in store
        assertNotNull(store.get("review_queue:" + id));

        // And retrievable via queue
        ReviewItem loaded = queue.get(id);
        assertNotNull(loaded);
        assertEquals("test content", loaded.getContent());
    }

    @Test
    void resolvePersistsResolution() {
        ReviewItem item = ReviewItem.of("content", "gate", List.of());
        String id = queue.submit(item);

        ReviewResolution res = queue.resolve(id, ReviewDecision.CONFIRM, "human");
        assertNotNull(res);

        // Resolution should be in store
        ReviewResolution loaded = queue.resolution(id);
        assertNotNull(loaded);
        assertEquals(ReviewDecision.CONFIRM, loaded.decision());
        assertEquals("human", loaded.resolvedBy());
    }

    @Test
    void pendingMergesLocalAndStore() {
        // Submit one item via this queue
        ReviewItem item1 = ReviewItem.of("local", "gate", List.of());
        queue.submit(item1);

        // Create another queue pointing to the same store (simulating cross-process)
        ReviewQueue otherQueue = new ReviewQueue(Set.of("human"), null, null, store, "review_queue");
        ReviewItem item2 = ReviewItem.of("remote", "gate", List.of());
        otherQueue.submit(item2);

        // Both should appear in pending
        List<ReviewItem> pending = queue.pending();
        assertTrue(pending.stream().anyMatch(i -> "local".equals(i.getContent())));
        assertTrue(pending.stream().anyMatch(i -> "remote".equals(i.getContent())));
    }

    @Test
    void pendingExcludesResolved() {
        ReviewItem item = ReviewItem.of("to-resolve", "gate", List.of());
        String id = queue.submit(item);

        // Before resolve
        assertEquals(1, queue.pending().size());

        // After resolve
        queue.resolve(id, ReviewDecision.CONFIRM, "human");
        List<ReviewItem> pending = queue.pending();
        assertTrue(pending.stream().noneMatch(i -> i.getId().equals(id)));
    }

    @Test
    void crossProcessVisibility() {
        // Queue A submits
        ReviewItem item = ReviewItem.of("cross-process", "gate", List.of());
        String id = queue.submit(item);

        // Queue B (same store, different "process") can see it
        ReviewQueue queueB = new ReviewQueue(Set.of("human"), null, null, store, "review_queue");
        assertTrue(queueB.isPending(id));

        // Queue B resolves
        queueB.resolve(id, ReviewDecision.REVISE, "human", "needs fix", "corrected content");

        // Queue A sees it resolved
        assertFalse(queue.isPending(id));
        ReviewResolution res = queue.resolution(id);
        assertEquals(ReviewDecision.REVISE, res.decision());
        assertEquals("corrected content", res.correctedContent());
    }

    @Test
    void escalateFromVerdictPersists() {
        List<Map<String, Object>> findings = List.of(
            Map.of("type", "security", "severity", "error", "message", "injection detected")
        );

        String id = queue.escalateFromVerdict(false, "malicious content", "deterministic_gate", findings);
        assertNotNull(id);

        // Should be in store
        ReviewItem loaded = queue.get(id);
        assertNotNull(loaded);
        assertEquals("malicious content", loaded.getContent());
    }

    @Test
    void verdictPassedReturnsNull() {
        String id = queue.escalateFromVerdict(true, "safe content", "gate", List.of());
        assertNull(id);
    }
}
