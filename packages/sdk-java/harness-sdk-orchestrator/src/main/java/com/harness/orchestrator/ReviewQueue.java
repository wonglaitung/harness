package com.harness.orchestrator;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Predicate;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.memory.BlackboardItem;
import com.harness.memory.StateStore;

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
 * <p>Optional store-backed persistence: pass a {@link StateStore} (SharedStateStore
 * or FileStateStore) to persist items and resolutions across process boundaries.</p>
 *
 * <h3>Usage</h3>
 * <pre>{@code
 * // In-memory (default)
 * ReviewQueue queue = new ReviewQueue(Set.of("human", "auditor:alice"));
 * String id = queue.submit(ReviewItem.of(content, "gate", findings));
 * ReviewResolution res = queue.resolve(id, ReviewDecision.CONFIRM, "human", null, null);
 *
 * // Store-backed (durable, cross-process)
 * StateStore store = new FileStateStore(Path.of(".harness/review.db"));
 * ReviewQueue durableQueue = new ReviewQueue(Set.of("human"), null, null, store, "review_queue");
 * }</pre>
 */
public class ReviewQueue {

    private static final Logger logger = LoggerFactory.getLogger(ReviewQueue.class);

    private final Set<String> humanActors;
    private final Predicate<String> verifyActor;
    private final ReviewSink sink;
    private final StateStore store;
    private final String namespace;

    /** In-memory item store (thread-safe). */
    private final Map<String, ReviewItem> items = new ConcurrentHashMap<>();

    /** In-memory resolution store. */
    private final Map<String, ReviewResolution> resolutions = new ConcurrentHashMap<>();

    /**
     * Create queue with default human actors ({"human"}), no identity verification, no sink.
     */
    public ReviewQueue() {
        this(Set.of("human"), null, null, null, "review_queue");
    }

    /**
     * Create queue with specified human actors.
     *
     * @param humanActors set of allowed actor identities
     */
    public ReviewQueue(Set<String> humanActors) {
        this(humanActors, null, null, null, "review_queue");
    }

    /**
     * Create queue with full configuration (in-memory).
     *
     * @param humanActors set of allowed actor identities (e.g., {"human", "auditor:alice"})
     * @param verifyActor optional predicate for real identity verification (accepts self-reported if null)
     * @param sink        optional sink for resolved decisions (KB/audit export)
     */
    public ReviewQueue(Set<String> humanActors, Predicate<String> verifyActor, ReviewSink sink) {
        this(humanActors, verifyActor, sink, null, "review_queue");
    }

    /**
     * Create queue with full configuration (optionally store-backed).
     *
     * @param humanActors set of allowed actor identities
     * @param verifyActor optional predicate for real identity verification
     * @param sink        optional sink for resolved decisions
     * @param store       optional state store for persistence (null = in-memory only)
     * @param namespace   store type prefix for review items (default "review_queue")
     */
    public ReviewQueue(
            Set<String> humanActors,
            Predicate<String> verifyActor,
            ReviewSink sink,
            StateStore store,
            String namespace) {
        this.humanActors = humanActors != null ? Set.copyOf(humanActors) : Set.of("human");
        this.verifyActor = verifyActor;
        this.sink = sink;
        this.store = store;
        this.namespace = namespace != null ? namespace : "review_queue";
    }

    // -- Store persistence helpers ------------------------------------------

    private String itemId(String id) {
        return namespace + ":" + id;
    }

    private String resolutionId(String id) {
        return namespace + ":res:" + id;
    }

    private void persistItem(ReviewItem item) {
        if (store == null) return;
        BlackboardItem bi = new BlackboardItem(
            itemId(item.getId()),
            namespace,
            Map.of(
                "id", item.getId(),
                "gateFindings", item.getGateFindings(),
                "content", item.getContent(),
                "source", item.getSource(),
                "metadata", item.getMetadata(),
                "resolved", false
            ),
            "review_queue",
            1.0f,
            0,
            3600,
            "confirmed",
            "harness",
            "harness",
            java.time.Instant.now()
        );
        store.put(bi);
    }

    private void persistResolution(ReviewResolution resolution) {
        if (store == null) return;
        BlackboardItem bi = new BlackboardItem(
            resolutionId(resolution.itemId()),
            namespace + ":resolution",
            Map.of(
                "itemId", resolution.itemId(),
                "decision", resolution.decision().name(),
                "resolvedBy", resolution.resolvedBy(),
                "reason", resolution.reason() != null ? resolution.reason() : "",
                "correctedContent", resolution.correctedContent() != null ? resolution.correctedContent() : "",
                "resolvedAt", resolution.resolvedAt().toString()
            ),
            "review_queue",
            1.0f,
            0,
            3600,
            "confirmed",
            "harness",
            "harness",
            java.time.Instant.now()
        );
        store.put(bi);
    }

    @SuppressWarnings("unchecked")
    private ReviewItem loadItem(String id) {
        if (store == null) return null;
        BlackboardItem bi = store.get(itemId(id));
        if (bi == null) return null;
        Map<String, Object> content = bi.content();
        List<Map<String, Object>> findings = (List<Map<String, Object>>) content.get("gateFindings");
        Map<String, String> metadata = (Map<String, String>) content.get("metadata");
        return new ReviewItem(findings, (String) content.get("content"),
            (String) content.get("source"), metadata);
    }

    @SuppressWarnings("unchecked")
    private ReviewResolution loadResolution(String id) {
        if (store == null) return null;
        BlackboardItem bi = store.get(resolutionId(id));
        if (bi == null) return null;
        Map<String, Object> content = bi.content();
        ReviewDecision decision = ReviewDecision.valueOf((String) content.get("decision"));
        String reason = (String) content.get("reason");
        String corrected = (String) content.get("correctedContent");
        return new ReviewResolution(
            (String) content.get("itemId"),
            decision,
            (String) content.get("resolvedBy"),
            reason != null && !reason.isEmpty() ? reason : null,
            corrected != null && !corrected.isEmpty() ? corrected : null,
            java.time.Instant.parse((String) content.get("resolvedAt"))
        );
    }

    // -- Public API ---------------------------------------------------------

    /**
     * Submit a review item to the queue.
     *
     * @param item the review item
     * @return the item ID (used for resolution)
     */
    public String submit(ReviewItem item) {
        Objects.requireNonNull(item, "ReviewItem must not be null");
        items.put(item.getId(), item);
        persistItem(item);
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

        // Check item exists (local or store)
        ReviewItem item = items.remove(itemId);
        if (item == null) {
            item = loadItem(itemId);
        }
        if (item == null) {
            throw new IllegalArgumentException("Review item not found: " + itemId);
        }

        // Critical-item guard (G3): ERROR-severity items only by human actors
        if ("error".equals(item.getMetadata().get("severity"))) {
            if (!humanActors.contains(actor)) {
                // Put item back
                items.put(itemId, item);
                persistItem(item);
                throw new IllegalStateException(
                    "Critical item (severity=error) can only be resolved by human actors: " + actor);
            }
        }

        // Check actor is in allowed set
        if (!humanActors.contains(actor)) {
            items.put(itemId, item);
            persistItem(item);
            throw new IllegalArgumentException(
                "Actor '" + actor + "' is not in humanActors: " + humanActors);
        }

        // Verify real identity (if predicate configured)
        if (verifyActor != null && !verifyActor.test(actor)) {
            items.put(itemId, item);
            persistItem(item);
            throw new IllegalStateException(
                "Identity verification failed for actor: " + actor);
        }

        // Build resolution record
        ReviewResolution resolution = switch (decision) {
            case CONFIRM -> ReviewResolution.confirm(itemId, actor);
            case REVISE -> ReviewResolution.revise(itemId, actor, correctedContent, reason);
            case EXEMPT -> ReviewResolution.exempt(itemId, actor, reason);
        };

        resolutions.put(itemId, resolution);
        persistResolution(resolution);

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
        if (items.containsKey(itemId)) return true;
        ReviewItem stored = loadItem(itemId);
        return stored != null;
    }

    /**
     * List unresolved items (across processes when store-backed).
     *
     * @return list of pending review items
     */
    public List<ReviewItem> pending() {
        Map<String, ReviewItem> merged = new ConcurrentHashMap<>(items);
        if (store != null) {
            List<BlackboardItem> storeItems = store.listItems();
            for (BlackboardItem bi : storeItems) {
                if (!namespace.equals(bi.type())) continue;
                try {
                    ReviewItem remote = loadItem(
                        ((String) bi.content().get("id")));
                    if (remote != null) {
                        merged.putIfAbsent(remote.getId(), remote);
                    }
                } catch (Exception e) {
                    logger.warn("Skipping malformed store item: {}", bi.getId());
                }
            }
        }
        List<ReviewItem> result = new ArrayList<>();
        for (ReviewItem item : merged.values()) {
            // Check if resolved
            if (resolutions.containsKey(item.getId())) continue;
            ReviewResolution storedRes = loadResolution(item.getId());
            if (storedRes != null) continue;
            result.add(item);
        }
        return result;
    }

    /**
     * Get the number of pending items.
     */
    public int getPendingCount() {
        return pending().size();
    }

    /**
     * Get a review item by ID.
     *
     * @param itemId item ID
     * @return the item, or null if not found
     */
    public ReviewItem get(String itemId) {
        ReviewItem item = items.get(itemId);
        if (item != null) return item;
        return loadItem(itemId);
    }

    /**
     * Get the resolution for a resolved item.
     *
     * @param itemId item ID
     * @return the resolution, or null if not resolved
     */
    public ReviewResolution resolution(String itemId) {
        ReviewResolution res = resolutions.get(itemId);
        if (res != null) return res;
        return loadResolution(itemId);
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
