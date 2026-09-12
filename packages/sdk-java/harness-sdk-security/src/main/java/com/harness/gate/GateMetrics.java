package com.harness.gate;

import java.util.HashMap;
import java.util.Map;

/**
 * F1/F2: Governance observability — deterministic, LLM-free metrics for the gate.
 *
 * <p>Accumulates governance outcomes (isolation_rate, coverage_rate, grounding_rate)
 * and exposes them via a queryable snapshot. Pure Java — no LLM involvement.</p>
 *
 * <h3>Named Governance Metrics</h3>
 * <ul>
 *   <li>{@code isolation_rate}: fraction of checks that were blocked (quarantined)</li>
 *   <li>{@code coverage_rate}: fraction of claims that were sourced (grounded)</li>
 *   <li>{@code grounding_rate}: 1 - (unsourced / total) claims</li>
 * </ul>
 */
public class GateMetrics {

    private int checks = 0;
    private int passed = 0;
    private int blocked = 0;
    private final Map<String, Integer> findingsByType = new HashMap<>();
    private final Map<String, Integer> findingsBySeverity = new HashMap<>();
    private int totalClaims = 0;
    private int sourcedClaims = 0;
    private int unsourcedClaims = 0;

    /**
     * Record a single gate verdict into running counters.
     */
    public void record(GateVerdict verdict) {
        checks++;
        if (verdict.passed()) {
            passed++;
        } else {
            blocked++;
        }
        for (GateFinding f : verdict.findings()) {
            String type = f.type().name();
            String severity = f.severity().name();
            findingsByType.merge(type, 1, Integer::sum);
            findingsBySeverity.merge(severity, 1, Integer::sum);

            // F1/F2: Track fact grounding outcomes
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

    /**
     * Record a finding directly (for use without a full GateVerdict).
     */
    public void recordFinding(GateFinding finding) {
        String type = finding.type().name();
        String severity = finding.severity().name();
        findingsByType.merge(type, 1, Integer::sum);
        findingsBySeverity.merge(severity, 1, Integer::sum);

        if (finding.id().startsWith("fact:")) {
            totalClaims++;
            if ("fact:no-source".equals(finding.id())) {
                unsourcedClaims++;
            } else {
                sourcedClaims++;
            }
        }
    }

    /**
     * Return a queryable snapshot of governance metrics.
     *
     * @param reviewBacklog optional review queue backlog count
     * @return snapshot map with all governance rates
     */
    public Map<String, Object> snapshot(Integer reviewBacklog) {
        Map<String, Object> out = new HashMap<>();
        out.put("checks", checks);
        out.put("passed", passed);
        out.put("blocked", blocked);
        out.put("findings_by_type", Map.copyOf(findingsByType));
        out.put("findings_by_severity", Map.copyOf(findingsBySeverity));

        // F1/F2: Named governance rates
        double isolationRate = checks > 0 ? (double) blocked / checks : 0.0;
        double coverageRate = totalClaims > 0 ? (double) sourcedClaims / totalClaims : 1.0;
        double groundingRate = totalClaims > 0
            ? 1.0 - ((double) unsourcedClaims / totalClaims)
            : 1.0;

        out.put("isolation_rate", Math.round(isolationRate * 10000.0) / 10000.0);
        out.put("coverage_rate", Math.round(coverageRate * 10000.0) / 10000.0);
        out.put("grounding_rate", Math.round(groundingRate * 10000.0) / 10000.0);
        out.put("total_claims", totalClaims);
        out.put("sourced_claims", sourcedClaims);
        out.put("unsourced_claims", unsourcedClaims);

        if (reviewBacklog != null) {
            out.put("review_backlog", reviewBacklog);
        }
        return out;
    }

    /**
     * Return a queryable snapshot without review backlog.
     */
    public Map<String, Object> snapshot() {
        return snapshot(null);
    }

    // Getters for direct access
    public int getChecks() { return checks; }
    public int getPassed() { return passed; }
    public int getBlocked() { return blocked; }
    public int getTotalClaims() { return totalClaims; }
    public int getSourcedClaims() { return sourcedClaims; }
    public int getUnsourcedClaims() { return unsourcedClaims; }
}
