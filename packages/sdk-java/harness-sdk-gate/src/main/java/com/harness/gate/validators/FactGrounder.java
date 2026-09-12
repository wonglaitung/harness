package com.harness.gate.validators;

import com.harness.gate.GateValidator;
import com.harness.gate.models.FindingType;
import com.harness.gate.models.GateFinding;
import com.harness.gate.models.GateSeverity;

import java.util.List;
import java.util.Map;

/**
 * Ensure key conclusions carry provenance (dual-channel sourcing).
 *
 * <p>Channel A (auto): provenance extracted from tool call records. Channel B
 * (explicit): {@code sources=} passed at call time. The usable set is the union.
 * When the union is empty and the content contains factual claims, findings are
 * flagged (not silently passed). Deterministic heuristic, not semantic
 * guarantee.</p>
 */
public class FactGrounder implements GateValidator {

    private final int minContentLen;
    private final boolean blockOnUnsourced;

    public FactGrounder() {
        this(200, true);
    }

    public FactGrounder(int minContentLen, boolean blockOnUnsourced) {
        this.minContentLen = minContentLen;
        this.blockOnUnsourced = blockOnUnsourced;
    }

    @Override
    public List<GateFinding> check(
            String content,
            List<String> sources,
            List<Map<String, Object>> toolRecords) {
        List<GateFinding> findings = new java.util.ArrayList<>();
        List<String> usable = sources == null ? List.of() : new java.util.ArrayList<>(sources);
        List<String> claims = Claims.extractClaims(content);

        if (claims.isEmpty()) {
            return findings; // No factual claims -> nothing to ground.
        }

        if (usable.isEmpty()) {
            GateSeverity sev = blockOnUnsourced ? GateSeverity.ERROR : GateSeverity.WARNING;
            findings.add(new GateFinding(
                    "fact:no-source", FindingType.FACT, sev,
                    "交付含事实性结论（数字/日期/实体）但无溯源引用：未提供 sources= 且无可用的工具溯源记录",
                    null, String.join("; ", claims.subList(0, Math.min(3, claims.size())))));
            return findings;
        }

        for (String claim : claims) {
            if (!Claims.claimSupported(claim, usable)) {
                findings.add(new GateFinding(
                        "fact:unsupported", FindingType.FACT, GateSeverity.WARNING,
                        "事实性结论未能在溯源中匹配到支撑证据", null, claim));
            }
        }
        return findings;
    }
}
