package com.harness.orchestrator;

/**
 * Resolution outcome for a review item (M6-G).
 *
 * <p>Maps 1:1 from {@link ReviewDecision} but represents the recorded outcome
 * after the review is complete.</p>
 */
public enum ReviewResolution {
    /** Confirmed: content accepted as-is. */
    CONFIRMED,
    /** Revised: content was modified before acceptance. */
    REVISED,
    /** Exempted: accepted with documented exemption. */
    EXEMPTED
}
