package com.harness.gate;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * D1/Deterministic Gate: composes FormatValidator + FactGrounder + LogicReconciler + Reconciler
 * into a single check pipeline.
 *
 * <p>This is the 100% deterministic code裁决 (M6-A). LLM does NOT participate in the verdict.
 * The gate runs first, then LLM output is demoted to observation-only.</p>
 *
 * <p>Fail-closed: if any ERROR finding is produced, the gate blocks delivery.</p>
 */
public class DeterministicGate {

    private final FormatValidator formatValidator;
    private final FactGrounder factGrounder;
    private final LogicReconciler logicReconciler;
    private final Reconciler reconciler;

    public DeterministicGate() {
        this.formatValidator = new FormatValidator();
        this.factGrounder = new FactGrounder();
        this.logicReconciler = new LogicReconciler();
        this.reconciler = new Reconciler(factGrounder);
    }

    public DeterministicGate(FormatValidator formatValidator, FactGrounder factGrounder,
                             LogicReconciler logicReconciler, Reconciler reconciler) {
        this.formatValidator = formatValidator;
        this.factGrounder = factGrounder;
        this.logicReconciler = logicReconciler;
        this.reconciler = reconciler;
    }

    /**
     * Run all validators and produce a gate verdict.
     *
     * @param content         the LLM output to validate
     * @param trustedSources  source identifiers considered authoritative
     * @param toolRecords     available tool call records
     * @param rules           declarative business rules (can be empty)
     * @return GateVerdict with findings and delivered_content
     */
    public GateVerdict check(String content, Set<String> trustedSources,
                             List<String> toolRecords, List<LogicReconciler.RuleSpec> rules) {
        List<GateFinding> allFindings = new ArrayList<>();

        // Step 1: Format validation (C1)
        allFindings.addAll(formatValidator.validate(content));

        // Step 2: Fact validation (C2) — skip if format check already failed with ERROR
        if (allFindings.stream().noneMatch(f -> f.severity() == GateSeverity.ERROR)) {
            allFindings.addAll(factGrounder.ground(content, trustedSources, toolRecords));
        }

        // Step 3: Logic validation (C3) — skip if format/fact already failed
        if (allFindings.stream().noneMatch(f -> f.severity() == GateSeverity.ERROR)) {
            allFindings.addAll(logicReconciler.reconcile(content, rules));
        }

        // Step 4: Reconciliation (D1/D3) — produce delivered_content
        Map<String, Object> reconReport = reconciler.reconcile(content, trustedSources, toolRecords);
        String deliveredContent = reconciler.redact(content, trustedSources, toolRecords);

        // Gate verdict: ERROR findings block delivery
        boolean hasErrors = allFindings.stream()
            .anyMatch(f -> f.severity() == GateSeverity.ERROR);

        if (hasErrors) {
            return GateVerdict.failed(allFindings, deliveredContent);
        }

        // Pass with warnings
        GateVerdict verdict = GateVerdict.passed(deliveredContent);
        // Reconstruct with findings
        return new GateVerdict(true, allFindings, deliveredContent, reconReport);
    }

    /**
     * Convenience: check without business rules.
     */
    public GateVerdict check(String content, Set<String> trustedSources, List<String> toolRecords) {
        return check(content, trustedSources, toolRecords, List.of());
    }

    /**
     * Convenience: check format only.
     */
    public GateVerdict checkFormat(String content) {
        List<GateFinding> findings = formatValidator.validate(content);
        boolean hasErrors = findings.stream().anyMatch(f -> f.severity() == GateSeverity.ERROR);
        if (hasErrors) {
            return GateVerdict.failed(findings, content);
        }
        return new GateVerdict(true, findings, content, Map.of());
    }
}
