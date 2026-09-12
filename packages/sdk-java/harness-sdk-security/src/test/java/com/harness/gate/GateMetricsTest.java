package com.harness.gate;

import static org.junit.jupiter.api.Assertions.*;

import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * F1/F2 tests for GateMetrics governance rates.
 */
class GateMetricsTest {

    private GateMetrics metrics;

    @BeforeEach
    void setUp() {
        metrics = new GateMetrics();
    }

    @Test
    void isolationRateZeroWhenNoChecks() {
        Map<String, Object> snap = metrics.snapshot();
        assertEquals(0.0, snap.get("isolation_rate"));
    }

    @Test
    void isolationRateCalculation() {
        // 3 checks: 1 passed, 2 blocked
        metrics.record(GateVerdict.passed("ok"));
        metrics.record(GateVerdict.failed(List.of(), "blocked1"));
        metrics.record(GateVerdict.failed(List.of(), "blocked2"));

        Map<String, Object> snap = metrics.snapshot();
        assertEquals(3, snap.get("checks"));
        assertEquals(2, snap.get("blocked"));
        // 2/3 ≈ 0.6667
        double rate = (double) snap.get("isolation_rate");
        assertTrue(rate > 0.66 && rate < 0.67, "isolation_rate should be ~0.6667, got " + rate);
    }

    @Test
    void coverageRateWithSourcedAndUnsourcedClaims() {
        GateFinding sourced1 = new GateFinding(
            "fact:sourced-1", FindingType.FACT, GateSeverity.WARNING, "ok", "");
        GateFinding sourced2 = new GateFinding(
            "fact:sourced-2", FindingType.FACT, GateSeverity.WARNING, "ok", "");
        GateFinding unsourced = new GateFinding(
            "fact:no-source", FindingType.FACT, GateSeverity.WARNING, "missing", "");

        metrics.recordFinding(sourced1);
        metrics.recordFinding(sourced2);
        metrics.recordFinding(unsourced);

        Map<String, Object> snap = metrics.snapshot();
        assertEquals(3, snap.get("total_claims"));
        assertEquals(2, snap.get("sourced_claims"));
        assertEquals(1, snap.get("unsourced_claims"));

        double coverage = (double) snap.get("coverage_rate");
        assertTrue(coverage > 0.66 && coverage < 0.67, "coverage_rate should be ~0.6667");

        double grounding = (double) snap.get("grounding_rate");
        assertTrue(grounding > 0.66 && grounding < 0.67, "grounding_rate should be ~0.6667");
    }

    @Test
    void coverageRateOneWhenNoClaims() {
        metrics.record(GateVerdict.passed("ok"));
        Map<String, Object> snap = metrics.snapshot();
        assertEquals(1.0, snap.get("coverage_rate"));
        assertEquals(1.0, snap.get("grounding_rate"));
    }

    @Test
    void snapshotIncludesAllFields() {
        metrics.record(GateVerdict.passed("ok"));
        Map<String, Object> snap = metrics.snapshot(5);

        assertTrue(snap.containsKey("isolation_rate"));
        assertTrue(snap.containsKey("coverage_rate"));
        assertTrue(snap.containsKey("grounding_rate"));
        assertTrue(snap.containsKey("total_claims"));
        assertTrue(snap.containsKey("sourced_claims"));
        assertTrue(snap.containsKey("unsourced_claims"));
        assertEquals(5, snap.get("review_backlog"));
    }

    @Test
    void nonFactFindingsNotCountedAsClaims() {
        GateFinding fmtFinding = new GateFinding(
            "fmt:empty", FindingType.FORMAT, GateSeverity.ERROR, "empty", "");
        GateFinding logicFinding = new GateFinding(
            "logic:sum-mismatch", FindingType.LOGIC, GateSeverity.ERROR, "mismatch", "");

        metrics.recordFinding(fmtFinding);
        metrics.recordFinding(logicFinding);

        Map<String, Object> snap = metrics.snapshot();
        assertEquals(0, snap.get("total_claims"));
        assertEquals(1.0, snap.get("coverage_rate"));
    }
}
