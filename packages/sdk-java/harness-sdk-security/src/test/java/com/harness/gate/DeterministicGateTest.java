package com.harness.gate;

import static org.junit.jupiter.api.Assertions.*;

import java.util.List;
import java.util.Set;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * Tests for DeterministicGate (C4 + D1/D3).
 */
class DeterministicGateTest {

    private DeterministicGate gate;

    @BeforeEach
    void setUp() {
        gate = new DeterministicGate();
    }

    @Test
    void emptyContentFailsFormatCheck() {
        var verdict = gate.check("", Set.of(), List.of());
        assertFalse(verdict.passed());
        assertTrue(verdict.findings().stream().anyMatch(f -> "fmt:empty".equals(f.id())));
    }

    @Test
    void normalContentPasses() {
        String content = "# Report\n\nSome content here.";
        var verdict = gate.check(content, Set.of(), List.of());
        assertTrue(verdict.passed());
        assertEquals(content, verdict.deliveredContent());
    }

    @Test
    void contentWithNullBytesFails() {
        String content = "Hello\u0000World";
        var verdict = gate.check(content, Set.of(), List.of());
        assertFalse(verdict.passed());
    }

    @Test
    void formatErrorBlocksFactChecking() {
        var verdict = gate.check(null, Set.of("source1"), List.of());
        assertFalse(verdict.passed());
        // Should have fmt:empty, not fact:no-source (fact check skipped)
        assertTrue(verdict.findings().stream().anyMatch(f -> "fmt:empty".equals(f.id())));
    }

    @Test
    void withBusinessRules() {
        String content = "Revenue: 500\nCost: 200\nTotal: 800";
        var rules = List.of(new LogicReconciler.RuleSpec(
            "numeric_sum", "Total", java.util.Map.of("components", List.of("Revenue", "Cost"))));
        var verdict = gate.check(content, Set.of(), List.of(), rules);
        // 500+200=700 but Total=800, so logic error
        assertFalse(verdict.passed());
        assertTrue(verdict.findings().stream().anyMatch(f -> "logic:sum-mismatch".equals(f.id())));
    }

    @Test
    void checkFormatOnly() {
        var verdict = gate.checkFormat("Normal content");
        assertTrue(verdict.passed());
    }
}
