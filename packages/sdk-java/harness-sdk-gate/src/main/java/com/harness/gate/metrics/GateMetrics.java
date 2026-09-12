package com.harness.gate.metrics;

import com.harness.gate.models.GateFinding;
import com.harness.gate.models.GateVerdict;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Governance observability — deterministic, LLM-free metrics for the gate.
 *
 * <p>Keeps accumulation logic pure and unit-testable so the harness can expose a
 * queryable snapshot without scraping logs.</p>
 *
 * <p>Named governance metrics:
 * <ul>
 *   <li>isolation_rate: fraction of checks that were blocked (quarantined)</li>
 *   <li>coverage_rate: fraction of claims that were sourced (grounded)</li>
 *   <li>grounding_rate: fraction of fact findings that were sourced</li>
 * </ul>
 * OpenTelemetry export is intentionally omitted in the Java port; callers can
 * bridge {@link #snapshot} to their own metrics backend.</p>
 */
public class GateMetrics {

    private int checks = 0;
    private int passed = 0;
    private int blocked = 0;
    private final Map<String, Integer> findingsByType = new LinkedHashMap<>();
    private final Map<String, Integer> findingsBySeverity = new LinkedHashMap<>();
    private int totalClaims = 0;
    private int sourcedClaims = 0;
    private int unsourcedClaims = 0;

    public void record(GateVerdict verdict) {
        checks++;
        if (verdict.passed()) {
            passed++;
        } else {
            blocked++;
        }
        for (GateFinding f : verdict.findings()) {
            String t = f.type().value();
            String s = f.severity().value();
            findingsByType.merge(t, 1, Integer::sum);
            findingsBySeverity.merge(s, 1, Integer::sum);
            if (f.id().startsWith("fact:")) {
                totalClaims++;
                if ("fact:no-source".equals(f.id())) {
                    unsourcedClaims++;
                } else {
                    sourcedClaims++;
                }
            }
        }
    }

    public Map<String, Object> snapshot(Integer reviewBacklog) {
        double isolationRate = checks > 0 ? (double) blocked / checks : 0.0;
        double coverageRate = totalClaims > 0 ? (double) sourcedClaims / totalClaims : 1.0;
        double groundingRate = totalClaims > 0 ? 1.0 - ((double) unsourcedClaims / totalClaims) : 1.0;
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("checks", checks);
        out.put("passed", passed);
        out.put("blocked", blocked);
        out.put("findings_by_type", new LinkedHashMap<>(findingsByType));
        out.put("findings_by_severity", new LinkedHashMap<>(findingsBySeverity));
        out.put("isolation_rate", round(isolationRate));
        out.put("coverage_rate", round(coverageRate));
        out.put("grounding_rate", round(groundingRate));
        out.put("total_claims", totalClaims);
        out.put("sourced_claims", sourcedClaims);
        out.put("unsourced_claims", unsourcedClaims);
        if (reviewBacklog != null) {
            out.put("review_backlog", reviewBacklog);
        }
        return out;
    }

    private static double round(double d) {
        return Math.round(d * 10000.0) / 10000.0;
    }
}
