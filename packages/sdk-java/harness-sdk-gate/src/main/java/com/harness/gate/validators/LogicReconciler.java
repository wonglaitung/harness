package com.harness.gate.validators;

import com.harness.gate.GateRule;
import com.harness.gate.GateValidator;
import com.harness.gate.models.FindingType;
import com.harness.gate.models.GateFinding;
import com.harness.gate.models.GateSeverity;

import java.util.List;
import java.util.Map;

/**
 * Apply user-supplied deterministic business rules.
 *
 * <p>Rules are pure functions {@code (content, sources) -> List<GateFinding>}.
 * The default set is empty; callers register cross-field / business invariants.</p>
 */
public class LogicReconciler implements GateValidator {

    private final List<GateRule> rules;

    public LogicReconciler() {
        this(List.of());
    }

    public LogicReconciler(List<GateRule> rules) {
        this.rules = rules == null ? List.of() : rules;
    }

    @Override
    public List<GateFinding> check(
            String content,
            List<String> sources,
            List<Map<String, Object>> toolRecords) {
        List<GateFinding> findings = new java.util.ArrayList<>();
        List<String> src = sources == null ? List.of() : sources;
        int i = 0;
        for (GateRule rule : rules) {
            try {
                findings.addAll(rule.check(content, src));
            } catch (Exception e) {
                // Rule failure must not crash the gate.
                findings.add(new GateFinding(
                        "logic:rule-" + i + "-error", FindingType.LOGIC, GateSeverity.WARNING,
                        "业务规则执行异常: " + e.getMessage()));
            }
            i++;
        }
        return findings;
    }
}
