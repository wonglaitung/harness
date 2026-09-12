package com.harness.gate;

import java.util.List;
import java.util.Map;

/**
 * Payload submitted to a {@link GateReviewSink} when a verdict fails.
 */
public record GateReviewItem(
        List<Map<String, Object>> gateFindings,
        String content,
        String source) {

    public GateReviewItem(List<Map<String, Object>> gateFindings, String content) {
        this(gateFindings, content, "deterministic_gate");
    }
}
