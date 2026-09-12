package com.harness.gate;

import java.util.List;
import java.util.Map;

/**
 * Verdict from the deterministic gate.
 *
 * @param passed               whether the gate passed (no ERROR findings)
 * @param findings             all findings from validators
 * @param deliveredContent     content to deliver (redacted if unsourced claims found)
 * @param reconciliationReport reconciliation report (claims vs sources)
 */
public record GateVerdict(
    boolean passed,
    List<GateFinding> findings,
    String deliveredContent,
    Map<String, Object> reconciliationReport
) {
    /**
     * Create a failed verdict.
     */
    public static GateVerdict failed(List<GateFinding> findings, String content) {
        return new GateVerdict(false, findings, content, Map.of());
    }

    /**
     * Create a passed verdict.
     */
    public static GateVerdict passed(String deliveredContent) {
        return new GateVerdict(true, List.of(), deliveredContent, Map.of());
    }
}
