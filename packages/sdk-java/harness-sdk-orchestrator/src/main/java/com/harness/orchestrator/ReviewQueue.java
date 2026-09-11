package com.harness.orchestrator;

import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Predicate;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Human review queue for deterministic gate findings (M6-G, enhanced).
 *
 * <p>Items are submitted when the deterministic gate flags content that requires
 * human judgment.  Only actors in {@code humanActors} may resolve items.
 * ERROR-severity items can ONLY be resolved by human actors (critical-item guard).</p>
 *
 * <p>M6 enhancements: rich {@link ReviewResolution} with resolved_by/reason/
 * corrected_content; critical-item guard blocks non-human resolution of
 * high-risk items.</p>
 *
 * <h3>Usage</h3>
 * <pre>{@code
 * ReviewQueue queue = new ReviewQueue(Set.of("human", "auditor:alice"));
 * String id = queue.submit(ReviewItem.of(content, "gate", findings));
 * ReviewResolution res = queue.resolve(id, ReviewDecision.CONFIRM, "human", null, null);
 * }</pre>
 */
public class ReviewQueue {

    private static final Logger logger = LoggerFactory.getLogger(ReviewQueue.class);

    private final Set<String> humanActors;
    private final Predicate<String> verifyActor;
    private final ReviewSink sink;

    /** In-memory item store (thread-safe). */
    private final Map<String, ReviewItem> items = new ConcurrentHashMap<>();

    /**
     * Create queue with default human actors ({"human"}), no identity verification, no sink.
     */
    public ReviewQueue() {
        this(Set.of("human"), null, null);
    }

    /**
     * Create queue with specified human actors.
     *
     * @param humanActors set of allowed actor identities
     */
    public ReviewQueue(Set<String> humanActors) {
        this(humanActors, null, null);
    }

    /**
     * Create queue with full configuration.
     *
     * @param humanActors set of allowed actor identities (e.g., {"human", "auditor:alice"})
     * @param verifyActor optional predicate for real identity verification (accepts self-reported if null)
     * @param sink        optional sink for resolved decisions (KB/audit export)
     */
    public ReviewQueue(Set<String> humanActors, Predicate<String> verifyActor, ReviewSink sink) {
        this.humanActors = humanActors != null ? Set.copyOf(humanActors) : Set.of("human");
        this.verifyActor = verifyActor;
        this.sink = sink;
    }

    /**
     * Submit a review item to the queue.
     *
     * @param item the review item
     * @return the item ID (used for resolution)
     */
    public String submit(ReviewItem item) {
        Objects.requireNonNull(item, "ReviewItem must not be null");
        items.put(item.getId(), item);
        logger.info("Review item submitted: {}", item.getId());
        return item.getId();
    }

    /**
     * Resolve a review item (basic: no reason/correction).
     *
     * @param itemId   ID of the item to resolve
     * @param decision human decision
     * @param actor    identity of the reviewer
     * @return the resolution record
     * @throws IllegalArgumentException if actor is not in {@code humanActors} or item not found
     * @throws IllegalStateException    if identity verification fails or critical-item guard blocks
     */
    public ReviewResolution resolve(String itemId, ReviewDecision decision, String actor) {
        return resolve(itemId, decision, actor, null, null);
    }

    /**
     * Resolve a review item with full context (M6-G enhanced).
     *
     * <p>Critical-item guard: if the item has {@code "severity"="error"} in
     * metadata, only actors in {@code humanActors} may resolve (no automation).</p>
     *
     * @param itemId           ID of the item to resolve
     * @param decision         human decision
     * @param actor            identity of the reviewer
     * @param reason           optional explanation (required for EXEMPT)
     * @param correctedContent optional corrected content (when decision is REVISE)
     * @return the resolution record
     * @throws IllegalArgumentException if actor not authorized or item not found
     * @throws IllegalStateException    if identity verification fails or critical-item guard blocks
     */
    public ReviewResolution resolve(
            String itemId,
            ReviewDecision decision,
            String actor,
            String reason,
            String correctedContent) {

        Objects.requireNonNull(itemId, "itemId must not be null");
        Objects.requireNonNull(decision, "decision must not be null");
        Objects.requireNonNull(actor, "actor must not be null");

        // Check item exists
        ReviewItem item = items.remove(itemId);
        if (item == null) {
            throw new IllegalArgumentException("Review item not found: " + itemId);
        }

        // Critical-item guard (G3): ERROR-severity items only by human actors
        if ("error".equals(item.getMetadata().get("severity"))) {
            if (!humanActors.contains(actor)) {
                // Put item back
                items.put(itemId, item);
                throw new IllegalStateException(
                    "Critical item (severity=error) can only be resolved by human actors: " + actor);
            }
        }

        // Check actor is in allowed set
        if (!humanActors.contains(actor)) {
            items.put(itemId, item);
            throw new IllegalArgumentException(
                "Actor '" + actor + "' is not in humanActors: " + humanActors);
        }

        // Verify real identity (if predicate configured)
        if (verifyActor != null && !verifyActor.test(actor)) {
            items.put(itemId, item);
            throw new IllegalStateException(
                "Identity verification failed for actor: " + actor);
        }

        // Build resolution record
        ReviewResolution resolution = switch (decision) {
            case CONFIRM -> ReviewResolution.confirm(itemId, actor);
            case REVISE -> ReviewResolution.revise(itemId, actor, correctedContent, reason);
            case EXEMPT -> ReviewResolution.exempt(itemId, actor, reason);
        };

        logger.info("Review item {} resolved by {}: {}", itemId, actor, resolution.decision());

        // Notify sink (exceptions swallowed)
        if (sink != null) {
            try {
                sink.onResolve(resolution, item);
            } catch (Exception e) {
                logger.warn("ReviewSink.onResolve failed for item {}: {}", itemId, e.getMessage());
            }
        }

        return resolution;
    }

    /**
     * Check if an item is still pending.
     */
    public boolean isPending(String itemId) {
        return items.containsKey(itemId);
    }

    /**
     * Get the number of pending items.
     */
    public int getPendingCount() {
        return items.size();
    }

    /**
     * Escalate a gate verdict to the review queue (M6-G utility).
     *
     * <p>Convenience method: if the verdict is not passed, auto-submits
     * a {@link ReviewItem} to the queue and returns the item ID.
     * Returns null if the verdict passed (no escalation needed).</p>
     *
     * @param verdictPassed whether the gate verdict passed
     * @param content       the content under review
     * @param source        origin (e.g., "deterministic_gate")
     * @param findings      gate findings (may be null)
     * @return item ID if escalated, null if passed
     */
    public String escalateFromVerdict(boolean verdictPassed, String content, String source,
                                       java.util.List<Map<String, Object>> findings) {
        if (verdictPassed) {
            return null;
        }
        ReviewItem item = ReviewItem.of(content, source, findings);
        return submit(item);
    }
}
