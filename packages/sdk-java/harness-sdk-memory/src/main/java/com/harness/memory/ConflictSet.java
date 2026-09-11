package com.harness.memory;

import java.time.Instant;

/**
 * Represents a set of conflicting blackboard items (M6-H).
 *
 * <p>When multiple agents propose contradictory facts for the same logical key,
 * the conflicting items are grouped into a ConflictSet for human resolution
 * instead of being silently overwritten.</p>
 *
 * @param key         logical key (e.g., "balance-check", "decision-X")
 * @param itemIds     IDs of the conflicting items
 * @param detectedAt  when the conflict was detected
 */
public record ConflictSet(
    String key,
    java.util.List<String> itemIds,
    Instant detectedAt
) {
    /**
     * Create a new conflict set.
     */
    public static ConflictSet create(String key, java.util.List<String> itemIds) {
        return new ConflictSet(key, java.util.List.copyOf(itemIds), Instant.now());
    }
}
