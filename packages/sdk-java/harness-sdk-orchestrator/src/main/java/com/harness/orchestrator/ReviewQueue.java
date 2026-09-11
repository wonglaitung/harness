package com.harness.orchestrator;

import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Predicate;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Human review queue for deterministic gate findings (M6-G).
 *
 * <p>Items are submitted when the deterministic gate flags content that requires
 * human judgment.  Only actors in {@code human_actors} may resolve items.
 * Optional {@code verifyActor} predicate provides real identity verification
 * (e.g., IdP integration); without it, actor identity is accepted as self-reported.</p>
 *
 * <p>Decision出口: optional {@link ReviewSink} receives each resolution for
 * persistence into a KB or audit log.  Sink exceptions are swallowed.</p>
 *
 * <h3>Usage</h3>
 * <pre>{@code
 * ReviewQueue queue = new ReviewQueue(Set.of("human", "auditor:alice"));
 * String id = queue.submit(ReviewItem.of(content, "gate", findings));
 * queue.resolve(id, ReviewDecision.CONFIRM, "human");
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
     * Resolve a review item.
     *
     * @param itemId   ID of the item to resolve
     * @param decision human decision
     * @param actor    identity of the reviewer
     * @throws IllegalArgumentException if actor is not in {@code humanActors} or item not found
     * @throws IllegalStateException    if identity verification fails
     */
    public void resolve(String itemId, ReviewDecision decision, String actor) {
        Objects.requireNonNull(itemId, "itemId must not be null");
        Objects.requireNonNull(decision, "decision must not be null");
        Objects.requireNonNull(actor, "actor must not be null");

        // Check item exists
        ReviewItem item = items.remove(itemId);
        if (item == null) {
            throw new IllegalArgumentException("Review item not found: " + itemId);
        }

        // Check actor is in allowed set
        if (!humanActors.contains(actor)) {
            throw new IllegalArgumentException(
                "Actor '" + actor + "' is not in human_actors: " + humanActors);
        }

        // Verify real identity (if predicate configured)
        if (verifyActor != null && !verifyActor.test(actor)) {
            throw new IllegalStateException(
                "Identity verification failed for actor: " + actor);
        }

        // Map decision to resolution
        ReviewResolution resolution = switch (decision) {
            case CONFIRM -> ReviewResolution.CONFIRMED;
            case REVISE -> ReviewResolution.REVISED;
            case EXEMPT -> ReviewResolution.EXEMPTED;
        };

        logger.info("Review item {} resolved by {}: {}", itemId, actor, resolution);

        // Notify sink (exceptions swallowed)
        if (sink != null) {
            try {
                sink.onResolve(resolution, item);
            } catch (Exception e) {
                logger.warn("ReviewSink.onResolve failed for item {}: {}", itemId, e.getMessage());
            }
        }
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
}
