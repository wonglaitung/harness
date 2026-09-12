package com.harness.gate;

import com.harness.gate.models.FindingType;
import com.harness.gate.models.GateFinding;
import com.harness.gate.models.GateSeverity;
import com.harness.gate.models.GateVerdict;
import com.harness.gate.reconciliation.Reconciler;
import com.harness.gate.validators.FactGrounder;
import com.harness.gate.validators.FormatValidator;
import com.harness.gate.validators.LogicReconciler;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * DeterministicGate — the single delivery-before-handoff checkpoint.
 *
 * <p>Composes the three validators (format / fact / logic) plus reconciliation
 * into one 100%-deterministic verdict. The LLM never decides; it only produces
 * the candidate content. When the verdict fails and a review sink is attached,
 * the findings are submitted for human-in-the-loop resolution.</p>
 */
public class DeterministicGate {

    private final List<GateValidator> validators;
    private final Reconciler reconciler;
    private final GateReviewSink reviewSink;

    public DeterministicGate() {
        this(null, null, null);
    }

    public DeterministicGate(
            List<GateValidator> validators,
            Reconciler reconciler,
            GateReviewSink reviewSink) {
        this.validators = validators != null
                ? validators
                : List.of(new FormatValidator(), new FactGrounder(), new LogicReconciler());
        this.reconciler = reconciler != null ? reconciler : new Reconciler();
        this.reviewSink = reviewSink;
    }

    public GateVerdict check(
            String content,
            List<String> sources,
            List<Map<String, Object>> toolRecords) {
        List<String> src = sources != null ? sources : List.of();
        List<GateFinding> findings = new ArrayList<>();
        for (GateValidator v : validators) {
            findings.addAll(v.check(content, src, toolRecords));
        }

        Map<String, Object> report = reconciler.reconcile(content, src, findings);

        Object u = report.get("unsourced_claims");
        List<?> unsourced = u instanceof List ? (List<?>) u : List.of();
        if (!unsourced.isEmpty()) {
            List<String> evidence = new ArrayList<>();
            for (int i = 0; i < Math.min(3, unsourced.size()); i++) {
                evidence.add(String.valueOf(unsourced.get(i)));
            }
            findings.add(new GateFinding(
                    "recon:unsourced", FindingType.RECONCILIATION, GateSeverity.WARNING,
                    "交付含 " + unsourced.size() + " 条无溯源结论，已在交付内容中隔离/标注",
                    null, String.join("; ", evidence)));
        }

        boolean passed = findings.stream().noneMatch(f -> f.severity() == GateSeverity.ERROR);

        // Delivery-time enforcement: never hand back the raw content.
        String deliveredContent = reconciler.redact(content, report);

        GateVerdict verdict = new GateVerdict(passed, findings, deliveredContent, report);

        if (!passed && reviewSink != null) {
            try {
                List<Map<String, Object>> fs = findings.stream().map(GateFinding::asDict).toList();
                reviewSink.submit(new GateReviewItem(fs, content));
            } catch (Exception ignore) {
                // Review submission must never block delivery.
            }
        }

        return verdict;
    }
}
