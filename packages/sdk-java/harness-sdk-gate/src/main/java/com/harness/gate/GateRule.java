package com.harness.gate;

import com.harness.gate.models.GateFinding;

import java.util.List;

/**
 * A rule is a pure function: (content, sources) -&gt; list of findings.
 * Mirrors the Python {@code GateRule} contract consumed by {@code LogicReconciler}.
 */
@FunctionalInterface
public interface GateRule {
    List<GateFinding> check(String content, List<String> sources);
}
