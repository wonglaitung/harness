package com.harness.gate;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * D1/D3: Delivery reconciler — cross-checks conclusions against trusted sources
 * and redacts unsourced claims before delivery.
 *
 * <p>Produces a reconciliation report and a redacted delivered_content that
 * may be shorter than the original (D3: accepts shorter, more accurate output).</p>
 */
public class Reconciler {

    private final FactGrounder factGrounder;

    public Reconciler() {
        this.factGrounder = new FactGrounder();
    }

    public Reconciler(FactGrounder factGrounder) {
        this.factGrounder = factGrounder;
    }

    /**
     * Reconcile content against trusted sources.
     *
     * @param content         the content to reconcile
     * @param trustedSources  source identifiers considered authoritative
     * @param toolRecords     available tool call records
     * @return reconciliation report with findings and delivered_content
     */
    public Map<String, Object> reconcile(String content, java.util.Set<String> trustedSources, List<String> toolRecords) {
        Map<String, Object> report = new LinkedHashMap<>();

        // Run fact grounding
        List<GateFinding> findings = factGrounder.ground(content, trustedSources, toolRecords);

        // Separate sourced vs unsourced findings
        List<GateFinding> unsourced = findings.stream()
            .filter(f -> "fact:no-source".equals(f.id()))
            .toList();

        List<GateFinding> otherFindings = findings.stream()
            .filter(f -> !"fact:no-source".equals(f.id()))
            .toList();

        // Build report
        report.put("checked_claims", findings.size());
        report.put("sourced_claims", findings.size() - unsourced.size());
        report.put("unsourced_claims", unsourced.size());
        report.put("findings", findings.stream().map(GateFinding::asDict).toList());
        report.put("other_findings", otherFindings.stream().map(GateFinding::asDict).toList());

        return report;
    }

    /**
     * Redact unsourced claims from content.
     *
     * <p>Unsourced factual claims are replaced with a quarantine marker.
     * Non-factual content (headings, formatting, etc.) is preserved.</p>
     *
     * @param content         the original content
     * @param trustedSources  source identifiers considered authoritative
     * @param toolRecords     available tool call records
     * @return redacted content with unsourced claims replaced
     */
    public String redact(String content, java.util.Set<String> trustedSources, List<String> toolRecords) {
        if (content == null || content.isBlank()) {
            return content;
        }

        List<GateFinding> findings = factGrounder.ground(content, trustedSources, toolRecords);

        String redacted = content;
        for (GateFinding f : findings) {
            if ("fact:no-source".equals(f.id()) && f.evidence() != null && !f.evidence().isEmpty()) {
                // Find the unsourced claim text in content and replace
                String claimText = f.evidence();
                // Truncate-safe search: find the claim in content
                int idx = redacted.indexOf(claimText);
                if (idx >= 0) {
                    redacted = redacted.substring(0, idx)
                        + "[已隔离:无溯源]"
                        + redacted.substring(idx + claimText.length());
                }
            }
        }

        return redacted;
    }
}
