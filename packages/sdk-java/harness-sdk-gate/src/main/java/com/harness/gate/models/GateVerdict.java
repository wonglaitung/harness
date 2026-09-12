package com.harness.gate.models;

import java.util.List;
import java.util.Map;

/**
 * Result of running the deterministic gate over a delivery.
 *
 * <p>When the verdict fails (ERROR-severity finding), {@link #deliveredContent()}
 * is the quarantined/redacted version produced by the reconciler — never the raw
 * input. Callers must deliver this field, not the original content.</p>
 */
public record GateVerdict(
        boolean passed,
        List<GateFinding> findings,
        String deliveredContent,
        Map<String, Object> reconciliationReport) {

    public GateVerdict {
        if (findings == null) {
            findings = List.of();
        }
        if (reconciliationReport == null) {
            reconciliationReport = Map.of();
        }
    }

    public List<GateFinding> errors() {
        return findings.stream()
                .filter(f -> f.severity() == GateSeverity.ERROR)
                .toList();
    }

    public List<GateFinding> warnings() {
        return findings.stream()
                .filter(f -> f.severity() == GateSeverity.WARNING)
                .toList();
    }

    public Map<String, Object> asDict() {
        Map<String, Object> m = new java.util.LinkedHashMap<>();
        m.put("passed", passed);
        m.put("findings", findings.stream().map(GateFinding::asDict).toList());
        m.put("delivered_content", deliveredContent);
        m.put("reconciliation_report", reconciliationReport);
        return m;
    }
}
