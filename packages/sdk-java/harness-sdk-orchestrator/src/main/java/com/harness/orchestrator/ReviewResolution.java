package com.harness.orchestrator;

import java.time.Instant;

/**
 * Resolution record for a review item (M6-G, enhanced).
 *
 * <p>Contains full context about how a review was resolved: who resolved it,
 * when, why, and any corrected content.  The {@link ReviewSink} receives this
 * record so it can persist the full audit trail.</p>
 *
 * @param itemId           ID of the resolved review item
 * @param decision         the review decision that was made
 * @param resolvedBy       identity of the reviewer
 * @param reason           optional explanation (required for EXEMPT)
 * @param correctedContent optional corrected content (when decision is REVISE)
 * @param resolvedAt       timestamp of resolution
 */
public record ReviewResolution(
    String itemId,
    ReviewDecision decision,
    String resolvedBy,
    String reason,
    String correctedContent,
    Instant resolvedAt
) {
    /**
     * Create a resolution for CONFIRM (no reason/correction needed).
     */
    public static ReviewResolution confirm(String itemId, String resolvedBy) {
        return new ReviewResolution(itemId, ReviewDecision.CONFIRM, resolvedBy, null, null, Instant.now());
    }

    /**
     * Create a resolution for REVISE with corrected content.
     */
    public static ReviewResolution revise(String itemId, String resolvedBy, String correctedContent, String reason) {
        return new ReviewResolution(itemId, ReviewDecision.REVISE, resolvedBy, reason, correctedContent, Instant.now());
    }

    /**
     * Create a resolution for EXEMPT with reason.
     */
    public static ReviewResolution exempt(String itemId, String resolvedBy, String reason) {
        return new ReviewResolution(itemId, ReviewDecision.EXEMPT, resolvedBy, reason, null, Instant.now());
    }
}
