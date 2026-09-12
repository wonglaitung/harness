package com.harness.gate.validators;

import com.harness.gate.models.GateFinding;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Shared factual-claim extraction for the deterministic gate.
 *
 * <p>Heuristic markers for factual claims that require provenance: numbers with
 * units, percentages, dates, money, and quarter labels. Mirrors the Python
 * {@code _CLAIM_PATTERN} / {@code _normalize_claim_text} with the same CJK-aware
 * boundary handling (M6-D: full-width digits, intra-digit spaces, HTML
 * entities).</p>
 */
public final class Claims {

    private static final Pattern CLAIM_RE = Pattern.compile(
            "(?<![\\dA-Za-z])\\d[\\d,.]*\\s?(?:%|％|percent|kg|km|m|s|USD|\\$|元|万元|万吨|亿元|倍|摄氏度|°C)(?!\\d)"
                    + "|(?<![\\d])(?:19|20)\\d{2}[-/年]\\d{1,2}(?:[-/月]\\d{1,2})?(?!\\d)"
                    + "|(?<![\\dA-Za-z])[Qq][1-4]\\s?\\d{4}(?!\\d)");

    private Claims() {
    }

    /**
     * Normalize text before claim extraction so obfuscated numbers are caught.
     */
    public static String normalize(String text) {
        if (text == null) {
            return "";
        }
        String t = java.text.Normalizer.normalize(text, java.text.Normalizer.Form.NFKC);
        // strip whitespace inserted *inside* a digit run ("2 0 2 4")
        t = t.replaceAll("(?<=\\d)\\s+(?=\\d)", "");
        // decode HTML/XML numeric entities (&#52; -> 4)
        t = htmlUnescape(t);
        return t;
    }

    public static List<String> extractClaims(String content) {
        String norm = normalize(content);
        Matcher m = CLAIM_RE.matcher(norm);
        List<String> out = new ArrayList<>();
        while (m.find()) {
            out.add(m.group());
        }
        return out;
    }

    /**
     * Extract claims against the RAW content (no normalization). Used by the
     * reconciler so the produced substrings are directly replaceable in the
     * original delivery during redaction.
     */
    public static List<String> extractClaimsRaw(String content) {
        if (content == null) {
            return List.of();
        }
        Matcher m = CLAIM_RE.matcher(content);
        List<String> out = new ArrayList<>();
        while (m.find()) {
            out.add(m.group());
        }
        return out;
    }

    public static boolean claimSupported(String claim, List<String> sources) {
        String needle = claim.strip();
        if (needle.length() > 40) {
            needle = needle.substring(0, 40);
        }
        for (String src : sources) {
            if (src != null && src.contains(needle)) {
                return true;
            }
        }
        return false;
    }

    private static String htmlUnescape(String s) {
        Matcher m = Pattern.compile("&#(x?[0-9A-Fa-f]+);").matcher(s);
        StringBuffer sb = new StringBuffer();
        while (m.find()) {
            String g = m.group(1);
            try {
                int code;
                if (g.startsWith("x") || g.startsWith("X")) {
                    code = Integer.parseInt(g.substring(1), 16);
                } else {
                    code = Integer.parseInt(g, 10);
                }
                m.appendReplacement(sb, Matcher.quoteReplacement(String.valueOf((char) code)));
            } catch (NumberFormatException e) {
                m.appendReplacement(sb, Matcher.quoteReplacement(m.group(0)));
            }
        }
        m.appendTail(sb);
        return sb.toString();
    }
}
