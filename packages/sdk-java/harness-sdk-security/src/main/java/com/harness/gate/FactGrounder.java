package com.harness.gate;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * C2: Fact grounder — extracts factual claims and verifies they have supporting sources.
 *
 * <p>Dual-channel sourcing: Channel A = tool call records, Channel B = explicit citations.</p>
 * <p>If a claim has no supporting source, a {@code fact:no-source} finding is emitted.</p>
 */
public class FactGrounder {

    /**
     * Patterns that indicate a factual claim worth checking.
     * Groups: (1) the claim text.
     */
    private static final Pattern[] CLAIM_PATTERNS = {
        Pattern.compile("(?:^|\\n)(?:[\\d]+[.)\\s]+)?(?:\\*\\s+)?(.+?(?:is|are|was|were|equals?|amounts? to|costs?|total[s]?|sum[s]?)[^.]*\\.)", Pattern.CASE_INSENSITIVE),
        Pattern.compile("(?:^|\\n)(?:[\\d]+[.)\\s]+)?(?:\\*\\s+)?(.+?(?:increase|decrease|rise|fall|grow|drop)[s]?(?:\\s+by)?[^.]*\\.)", Pattern.CASE_INSENSITIVE),
        Pattern.compile("(?:^|\\n)(?:[\\d]+[.)\\s]+)?(?:\\*\\s+)?(.+?(?:\\$|€|£|¥)\\s*[\\d,]+[^.]*\\.)"),
    };

    /**
     * Source patterns that indicate a citation or reference.
     */
    private static final Pattern[] SOURCE_PATTERNS = {
        Pattern.compile("\\[([^\\]]+)\\]\\(([^)]+)\\)"),  // Markdown links
        Pattern.compile("(?:source|ref|reference|cite|出处|来源|参考)\\s*[:：]\\s*(.+)", Pattern.CASE_INSENSITIVE),
        Pattern.compile("(?:第\\s*\\d+\\s*页|page\\s+\\d+)", Pattern.CASE_INSENSITIVE),
    };

    /**
     * Ground claims against trusted sources.
     *
     * @param content         the content to check
     * @param trustedSources  source identifiers considered authoritative
     * @param toolRecords     available tool call records (Channel A)
     * @return list of findings (empty = all claims grounded)
     */
    public List<GateFinding> ground(String content, Set<String> trustedSources, List<String> toolRecords) {
        List<GateFinding> findings = new ArrayList<>();

        if (content == null || content.isBlank()) {
            return findings;
        }

        // Extract claims
        List<String> claims = extractClaims(content);

        // Extract sources from content (Channel B: explicit citations)
        List<String> explicitSources = extractExplicitSources(content);

        // Build source set: tool records + explicit sources
        List<String> allSources = new ArrayList<>();
        if (toolRecords != null) {
            allSources.addAll(toolRecords);
        }
        allSources.addAll(explicitSources);

        // Check each claim
        for (String claim : claims) {
            boolean grounded = false;

            // Check if claim text contains a trusted source reference
            for (String src : allSources) {
                if (claim.contains(src)) {
                    grounded = true;
                    break;
                }
            }

            // Check if claim references page numbers or document sections
            if (!grounded) {
                for (Pattern sp : SOURCE_PATTERNS) {
                    Matcher m = sp.matcher(claim);
                    if (m.find()) {
                        grounded = true;
                        break;
                    }
                }
            }

            if (!grounded) {
                findings.add(new GateFinding(
                    "fact:no-source", FindingType.FACT, GateSeverity.WARNING,
                    "Claim has no supporting source: " + truncate(claim, 100),
                    truncate(claim, 200)));
            }
        }

        return findings;
    }

    /**
     * Extract factual claims from content.
     */
    private List<String> extractClaims(String content) {
        List<String> claims = new ArrayList<>();
        for (Pattern p : CLAIM_PATTERNS) {
            Matcher m = p.matcher(content);
            while (m.find()) {
                String claim = m.group(1).trim();
                if (!claim.isEmpty() && claim.length() > 10) {
                    claims.add(claim);
                }
            }
        }
        return claims;
    }

    /**
     * Extract explicit source citations from content.
     */
    private List<String> extractExplicitSources(String content) {
        List<String> sources = new ArrayList<>();
        for (Pattern p : SOURCE_PATTERNS) {
            Matcher m = p.matcher(content);
            while (m.find()) {
                sources.add(m.group(0));
            }
        }
        return sources;
    }

    private static String truncate(String s, int maxLen) {
        if (s == null) return "";
        return s.length() <= maxLen ? s : s.substring(0, maxLen - 3) + "...";
    }
}
