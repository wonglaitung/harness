package com.harness.orchestrator;

import static org.junit.jupiter.api.Assertions.*;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.atomic.AtomicReference;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * M6-G tests for ReviewQueue, ReviewSink, ReviewResolution.
 * Mirrors Python test_m6_hardening.py coverage.
 */
class ReviewQueueM6Test {

    private ReviewQueue queue;

    @BeforeEach
    void setUp() {
        queue = new ReviewQueue(Set.of("human", "auditor:alice"));
    }

    // ---- submit / resolve lifecycle ----

    @Test
    void submitAndResolve() {
        ReviewItem item = ReviewItem.of("test content", "gate", List.of());
        String id = queue.submit(item);
        assertNotNull(id);
        assertTrue(queue.isPending(id));
        assertEquals(1, queue.getPendingCount());

        ReviewResolution res = queue.resolve(id, ReviewDecision.CONFIRM, "human");
        assertEquals(ReviewDecision.CONFIRM, res.decision());
        assertEquals("human", res.resolvedBy());
        assertEquals(id, res.itemId());
        assertNotNull(res.resolvedAt());
        assertFalse(queue.isPending(id));
        assertEquals(0, queue.getPendingCount());
    }

    // ---- ReviewSink callback ----

    @Test
    void sinkCalledOnResolve() {
        AtomicReference<ReviewResolution> capturedResolution = new AtomicReference<>();
        AtomicReference<ReviewItem> capturedItem = new AtomicReference<>();

        ReviewQueue q = new ReviewQueue(Set.of("human"), null,
            (resolution, item) -> {
                capturedResolution.set(resolution);
                capturedItem.set(item);
            });

        ReviewItem item = ReviewItem.of("content", "gate", List.of());
        String id = q.submit(item);
        q.resolve(id, ReviewDecision.CONFIRM, "human");

        assertNotNull(capturedResolution.get());
        assertEquals(ReviewDecision.CONFIRM, capturedResolution.get().decision());
        assertEquals(item.getId(), capturedItem.get().getId());
    }

    @Test
    void sinkExceptionIsSwallowed() {
        ReviewQueue q = new ReviewQueue(Set.of("human"), null,
            (resolution, item) -> { throw new RuntimeException("KB down"); });

        String id = q.submit(ReviewItem.of("content", "gate", List.of()));
        // Should not throw
        assertDoesNotThrow(() -> q.resolve(id, ReviewDecision.CONFIRM, "human"));
    }

    // ---- Actor authorization ----

    @Test
    void unauthorizedActorRejected() {
        String id = queue.submit(ReviewItem.of("content", "gate", List.of()));
        assertThrows(IllegalArgumentException.class,
            () -> queue.resolve(id, ReviewDecision.CONFIRM, "bot"));
    }

    // ---- Identity verification ----

    @Test
    void verifyActorFailureRejected() {
        ReviewQueue q = new ReviewQueue(Set.of("human"), actor -> false, null);
        String id = q.submit(ReviewItem.of("content", "gate", List.of()));
        assertThrows(IllegalStateException.class,
            () -> q.resolve(id, ReviewDecision.CONFIRM, "human"));
    }

    // ---- Critical-item guard (G3) ----

    @Test
    void criticalItemOnlyByHumanActors() {
        ReviewItem item = new ReviewItem(
            List.of(), "content", "gate",
            Map.of("severity", "error"));
        String id = queue.submit(item);

        // Non-human actor blocked
        assertThrows(IllegalStateException.class,
            () -> queue.resolve(id, ReviewDecision.CONFIRM, "auditor:alice"));

        // Human actor allowed
        assertDoesNotThrow(
            () -> queue.resolve(id, ReviewDecision.CONFIRM, "human"));
    }

    // ---- REVISE with corrected content ----

    @Test
    void reviseWithCorrectedContent() {
        String id = queue.submit(ReviewItem.of("bad content", "gate", List.of()));
        ReviewResolution res = queue.resolve(id, ReviewDecision.REVISE, "human",
            "needed fix", "corrected content");
        assertEquals(ReviewDecision.REVISE, res.decision());
        assertEquals("corrected content", res.correctedContent());
        assertEquals("needed fix", res.reason());
    }

    // ---- EXEMPT with reason ----

    @Test
    void exemptWithReason() {
        String id = queue.submit(ReviewItem.of("content", "gate", List.of()));
        ReviewResolution res = queue.resolve(id, ReviewDecision.EXEMPT, "human",
            "low risk, acceptable", null);
        assertEquals(ReviewDecision.EXEMPT, res.decision());
        assertEquals("low risk, acceptable", res.reason());
    }

    // ---- escalateFromVerdict ----

    @Test
    void escalateFromVerdictReturnsIdWhenFailed() {
        String id = queue.escalateFromVerdict(false, "content", "gate", List.of());
        assertNotNull(id);
        assertTrue(queue.isPending(id));
    }

    @Test
    void escalateFromVerdictReturnsNullWhenPassed() {
        String id = queue.escalateFromVerdict(true, "content", "gate", List.of());
        assertNull(id);
    }

    // ---- Item not found ----

    @Test
    void resolveNonexistentItemThrows() {
        assertThrows(IllegalArgumentException.class,
            () -> queue.resolve("nonexistent", ReviewDecision.CONFIRM, "human"));
    }
}
