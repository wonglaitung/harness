package com.harness.orchestrator;

/**
 * Sink for resolved review decisions (M6-G).
 *
 * <p>Implementations persist/harvest review outcomes into a knowledge base,
 * audit log, or external system.  The {@link ReviewQueue} calls
 * {@link #onResolve} after each successful {@code resolve()}.  Exceptions
 * thrown by the sink are swallowed (must not block the review flow).</p>
 *
 * <p>Kept as an interface so the SDK core stays decoupled from any particular
 * KB or audit backend.</p>
 */
public interface ReviewSink {

    /**
     * Called when a review item is resolved.
     *
     * @param resolution the resolution outcome
     * @param item       the original review item
     */
    void onResolve(ReviewResolution resolution, ReviewItem item);
}
