package com.harness.orchestrator;

/**
 * Sink for resolved review decisions (M6-G).
 *
 * <p>Implementations persist/harvest review outcomes into a knowledge base,
 * audit log, or external system.  The {@link ReviewQueue} calls
 * {@link #onResolve} after each successful {@code resolve()}.  Exceptions
 * thrown by the sink are swallowed (must not block the review flow).</p>
 *
 * <p>Receives the full {@link ReviewResolution} record (not just the enum)
 * so the sink has complete audit context: who resolved, when, why, and any
 * corrected content.</p>
 */
public interface ReviewSink {

    /**
     * Called when a review item is resolved.
     *
     * @param resolution the full resolution record (includes resolvedBy, reason, etc.)
     * @param item       the original review item
     */
    void onResolve(ReviewResolution resolution, ReviewItem item);
}
