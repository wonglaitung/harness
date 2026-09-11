package com.harness.memory;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Predicate;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Shared state store for multi-agent blackboard collaboration (M6-H).
 *
 * <p>Thread-safe in-memory implementation with CAS (Compare-And-Swap) concurrency
 * control.  Supports optional write and read verifiers for governance enforcement.</p>
 *
 * <h3>Write Layers</h3>
 * <ul>
 *   <li>{@code additive} — observations/proposals from any agent</li>
 *   <li>{@code authoritative} — decisions that require write-verifier approval</li>
 * </ul>
 *
 * <h3>Read Verification (M6-H)</h3>
 * <p>When {@code readVerifierRaise=true} and a {@code readVerifier} is set,
 * forged or forbidden authoritative items cause a {@link SecurityException}
 * instead of being silently dropped.</p>
 *
 * <h3>CAS Concurrency</h3>
 * <p>{@link #writeIfVersion} atomically checks the base version before writing.
 * If the version has moved, the write is rejected (caller may retry or create
 * a parallel proposal).</p>
 *
 * <h3>Usage</h3>
 * <pre>{@code
 * SharedStateStore store = new SharedStateStore(true); // readVerifierRaise=true
 * BlackboardItem item = BlackboardItem.create("decision", content, "planner", 0.9f, "harness");
 * store.put(item);
 * // CAS write
 * store.writeIfVersion(item.getId(), newContent, 0);
 * }</pre>
 */
public class SharedStateStore {

    private static final Logger logger = LoggerFactory.getLogger(SharedStateStore.class);

    /** Authorized writers for authoritative writes. */
    private static final Set<String> DEFAULT_AUTHORIZED_WRITERS = Set.of("harness", "orchestrator");

    /** Authorized readers for read verification. */
    private static final Set<String> DEFAULT_AUTHORIZED_READERS = Set.of("harness", "orchestrator", "audit");

    private final ConcurrentHashMap<String, BlackboardItem> items = new ConcurrentHashMap<>();

    private final boolean readVerifierRaise;
    private final Predicate<BlackboardItem> writeVerifier;
    private final Predicate<BlackboardItem> readVerifier;

    /**
     * Create store with no verifiers, no raise.
     */
    public SharedStateStore() {
        this(false, null, null);
    }

    /**
     * Create store with read verifier raise flag.
     *
     * @param readVerifierRaise if true, forged/forbidden reads throw SecurityException
     */
    public SharedStateStore(boolean readVerifierRaise) {
        this(readVerifierRaise, null, null);
    }

    /**
     * Create store with full configuration.
     *
     * @param readVerifierRaise if true, forged/forbidden reads throw SecurityException
     * @param writeVerifier     optional predicate for authoritative write approval
     * @param readVerifier      optional predicate for read authorization check
     */
    public SharedStateStore(
            boolean readVerifierRaise,
            Predicate<BlackboardItem> writeVerifier,
            Predicate<BlackboardItem> readVerifier) {
        this.readVerifierRaise = readVerifierRaise;
        this.writeVerifier = writeVerifier;
        this.readVerifier = readVerifier;
    }

    /**
     * Put an item into the store.
     *
     * @param item the blackboard item
     * @throws IllegalArgumentException if write verifier rejects the item
     */
    public void put(BlackboardItem item) {
        Objects.requireNonNull(item, "BlackboardItem must not be null");

        // Authoritative writes require write-verifier approval
        if ("authoritative".equals(item.type()) && writeVerifier != null) {
            if (!writeVerifier.test(item)) {
                throw new IllegalArgumentException(
                    "Write verifier rejected authoritative item: " + item.getId());
            }
        }

        items.put(item.getId(), item);
        logger.debug("Put item {}: type={}, source={}", item.getId(), item.type(), item.sourceAgent());
    }

    /**
     * Get an item by ID.
     *
     * @param id item ID
     * @return the item, or null if not found
     * @throws SecurityException if readVerifierRaise=true and readVerifier rejects the item
     */
    public BlackboardItem get(String id) {
        BlackboardItem item = items.get(id);
        if (item == null) {
            return null;
        }

        // Filter expired items
        if (item.isExpired()) {
            items.remove(id);
            return null;
        }

        // Read verification (M6-H)
        if (readVerifier != null && !readVerifier.test(item)) {
            if (readVerifierRaise) {
                throw new SecurityException(
                    "Forged/forbidden authoritative item rejected by readVerifier (H): " + id);
            }
            logger.warn("Read verifier rejected item {} (silently dropping)", id);
            return null;
        }

        return item;
    }

    /**
     * List all active (non-expired) items.
     *
     * @return list of items
     */
    public List<BlackboardItem> listItems() {
        List<BlackboardItem> result = new ArrayList<>();
        for (BlackboardItem item : items.values()) {
            if (item.isExpired()) {
                items.remove(item.getId());
                continue;
            }

            // Read verification (M6-H)
            if (readVerifier != null && !readVerifier.test(item)) {
                if (readVerifierRaise) {
                    throw new SecurityException(
                        "Forged/forbidden authoritative item rejected by readVerifier (H): " + item.getId());
                }
                logger.warn("Read verifier rejected item {} (silently dropping)", item.getId());
                continue;
            }

            result.add(item);
        }
        return List.copyOf(result);
    }

    /**
     * CAS (Compare-And-Swap) write: update content only if the base version matches.
     *
     * <p>If the version has moved, the write is rejected and the caller should
     * create a parallel proposal or retry.</p>
     *
     * @param id          item ID
     * @param newContent  new content to write
     * @param baseVersion expected current version
     * @return true if write succeeded, false if version mismatch
     * @throws IllegalArgumentException if item not found
     */
    public boolean writeIfVersion(String id, Map<String, Object> newContent, int baseVersion) {
        BlackboardItem current = items.get(id);
        if (current == null) {
            throw new IllegalArgumentException("Item not found: " + id);
        }

        if (current.baseVersion() != baseVersion) {
            logger.warn("CAS version mismatch for item {}: expected={}, actual={}",
                id, baseVersion, current.baseVersion());
            return false;
        }

        // Authoritative writes require write-verifier approval
        if ("authoritative".equals(current.type()) && writeVerifier != null) {
            BlackboardItem candidate = new BlackboardItem(
                current.id(), current.type(), newContent, current.sourceAgent(),
                current.confidence(), current.baseVersion() + 1, current.ttlSeconds(),
                current.status(), current.writerId(), current.effectiveWriter(),
                current.createdAt());
            if (!writeVerifier.test(candidate)) {
                throw new IllegalArgumentException(
                    "Write verifier rejected authoritative CAS write: " + id);
            }
        }

        BlackboardItem updated = new BlackboardItem(
            current.id(), current.type(), newContent, current.sourceAgent(),
            current.confidence(), current.baseVersion() + 1, current.ttlSeconds(),
            current.status(), current.writerId(), current.effectiveWriter(),
            current.createdAt());

        items.put(id, updated);
        logger.debug("CAS write succeeded for item {}: v{} → v{}", id, baseVersion, baseVersion + 1);
        return true;
    }

    /**
     * Get the current version of an item.
     *
     * @param id item ID
     * @return current base version, or -1 if not found
     */
    public int getVersion(String id) {
        BlackboardItem item = items.get(id);
        return item != null ? item.baseVersion() : -1;
    }

    /**
     * Get the number of active items.
     */
    public int size() {
        return items.size();
    }
}
