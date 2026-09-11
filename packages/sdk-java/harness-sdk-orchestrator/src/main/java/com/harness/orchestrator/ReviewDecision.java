package com.harness.orchestrator;

/**
 * Human review decision options (M6-G).
 *
 * <p>Presented to the reviewer for each {@link ReviewItem}.</p>
 */
public enum ReviewDecision {
    /** Content is correct as-is. */
    CONFIRM,
    /** Content needs revision (reviewer may provide corrections). */
    REVISE,
    /** Content is exempted from further review (with documented justification). */
    EXEMPT
}
