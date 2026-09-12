package com.harness.gate.reconciliation;

import com.harness.gate.validators.Claims;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Delivery-time reconciliation.
 *
 * <p>Cross-checks each extracted factual claim against the trusted-source fields
 * (collected by {@code FactGrounder}). The result is a structured report so the
 * caller can decide whether to strip/flag unsourced conclusions rather than
 * silently delivering them.</p>
 */
public class Reconciler {

    public Map<String, Object> reconcile(String content, List<String> sources, List<?> findings) {
        List<String> claims = Claims.extractClaimsRaw(content);
        if (claims.isEmpty()) {
            Map<String, Object> r = new LinkedHashMap<>();
            r.put("checked_claims", 0);
            r.put("sourced_claims", 0);
            r.put("unsourced_claims", List.of());
            r.put("source_count", sources == null ? 0 : sources.size());
            return r;
        }

        List<String> unsourced = new ArrayList<>();
        int sourced = 0;
        for (String claim : claims) {
            String needle = claim.strip();
            final String key = needle.length() > 40 ? needle.substring(0, 40) : needle;
            boolean ok = sources != null
                    && sources.stream().anyMatch(s -> s != null && s.contains(key));
            if (ok) {
                sourced++;
            } else {
                unsourced.add(claim);
            }
        }

        Map<String, Object> r = new LinkedHashMap<>();
        r.put("checked_claims", claims.size());
        r.put("sourced_claims", sourced);
        r.put("unsourced_claims", unsourced);
        r.put("source_count", sources == null ? 0 : sources.size());
        return r;
    }

    /**
     * Produce a delivery-safe version by quarantining unsourced claims. Each claim
     * that could not be grounded is replaced with a visible marker. When nothing
     * can be grounded (verdict still failed), a hard quarantine notice is
     * returned so the raw content is never silently delivered.
     */
    public static String redact(String content, Map<String, Object> report) {
        Object u = report == null ? null : report.get("unsourced_claims");
        List<?> unsourced = u instanceof List ? (List<?>) u : List.of();
        String safe = content;
        for (Object o : unsourced) {
            String claim = (String) o;
            if (claim != null && safe.contains(claim)) {
                safe = safe.replace(claim, "[已隔离:无溯源]");
            }
        }
        if (unsourced.isEmpty() || safe.strip().equals(content.strip())) {
            return "[内容未通过确定性闸门（含错误级发现），已隔离，不交付原始内容]";
        }
        return safe;
    }
}
