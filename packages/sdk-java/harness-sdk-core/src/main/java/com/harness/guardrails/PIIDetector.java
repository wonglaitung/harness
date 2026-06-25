package com.harness.guardrails;

import java.util.*;
import java.util.regex.*;

/**
 * PII Detector for Chinese and international PII patterns.
 *
 * Supports detection of:
 * - Chinese mobile phone numbers
 * - Chinese ID card numbers
 * - Chinese bank card numbers
 * - Chinese passport numbers
 * - Chinese social credit codes
 * - Chinese license plates
 * - Email addresses
 * - IP addresses
 *
 * Example:
 * <pre>
 * PIIDetector detector = PIIDetector.create();
 *
 * String text = "我的手机号是 13812345678，身份证是 110101199001011234";
 * List&lt;PIIEntity&gt; entities = detector.detect(text);
 *
 * for (PIIEntity entity : entities) {
 *     System.out.println(entity);
 * }
 *
 * // Redact PII
 * String redacted = detector.redact(text);
 * </pre>
 */
public class PIIDetector {

    private final List<PIIPattern> patterns;
    private final boolean includeNames;

    private PIIDetector(List<PIIPattern> patterns, boolean includeNames) {
        this.patterns = patterns;
        this.includeNames = includeNames;
    }

    /**
     * Create detector with all patterns.
     */
    public static PIIDetector create() {
        return builder().build();
    }

    /**
     * Create detector with default patterns (no name detection).
     */
    public static PIIDetector createDefault() {
        return builder().includeNames(false).build();
    }

    /**
     * Detect PII in text.
     */
    public List<PIIEntity> detect(String text) {
        List<PIIEntity> entities = new ArrayList<>();

        for (PIIPattern pattern : patterns) {
            Matcher matcher = pattern.pattern().matcher(text);
            while (matcher.find()) {
                String value = matcher.group();
                entities.add(new PIIEntity(
                    pattern.type(),
                    value,
                    matcher.start(),
                    matcher.end(),
                    pattern.confidence()
                ));
            }
        }

        // Sort by start position
        entities.sort(Comparator.comparingInt(PIIEntity::getStart));

        return entities;
    }

    /**
     * Check if text contains PII.
     */
    public boolean containsPII(String text) {
        for (PIIPattern pattern : patterns) {
            if (pattern.pattern().matcher(text).find()) {
                return true;
            }
        }
        return false;
    }

    /**
     * Redact PII in text.
     */
    public String redact(String text) {
        return redact(text, null);
    }

    /**
     * Redact PII in text with custom mask.
     */
    public String redact(String text, String mask) {
        List<PIIEntity> entities = detect(text);
        if (entities.isEmpty()) {
            return text;
        }

        // Sort by start position descending to avoid index shifting
        entities.sort((a, b) -> Integer.compare(b.getStart(), a.getStart()));

        String result = text;
        for (PIIEntity entity : entities) {
            String entityMask = mask != null ? mask : "[REDACTED_" + entity.getType().getCode().toUpperCase() + "]";
            result = entity.redact(result, entityMask);
        }

        return result;
    }

    /**
     * Scan text and return summary.
     */
    public Map<String, Integer> scan(String text) {
        List<PIIEntity> entities = detect(text);
        Map<String, Integer> summary = new HashMap<>();

        for (PIIEntity entity : entities) {
            String key = entity.getType().getCode();
            summary.put(key, summary.getOrDefault(key, 0) + 1);
        }

        return summary;
    }

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private boolean includeNames = false;
        private List<PIIEntity.Type> enabledTypes = null;

        public Builder includeNames(boolean v) {
            this.includeNames = v;
            return this;
        }

        public Builder enabledTypes(List<PIIEntity.Type> v) {
            this.enabledTypes = v;
            return this;
        }

        public PIIDetector build() {
            List<PIIPattern> allPatterns = getDefaultPatterns();
            return new PIIDetector(allPatterns, includeNames);
        }
    }

    // -------------------------------------------------------------------------
    // PII Patterns
    // -------------------------------------------------------------------------

    private static List<PIIPattern> getDefaultPatterns() {
        return List.of(
            // Chinese mobile phone: 1xxxxxxxxxx
            new PIIPattern(
                PIIEntity.Type.PHONE,
                Pattern.compile("(?<!\\d)1[3-9]\\d{9}(?!\\d)"),
                0.95
            ),

            // Chinese ID card: 18 digits
            new PIIPattern(
                PIIEntity.Type.ID_CARD,
                Pattern.compile("(?<!\\d)\\d{17}[\\dXx](?!\\d)"),
                0.9
            ),

            // Chinese bank card: 16-19 digits
            new PIIPattern(
                PIIEntity.Type.BANK_CARD,
                Pattern.compile("(?<!\\d)\\d{16,19}(?!\\d)"),
                0.7
            ),

            // Chinese passport: Gxxxxxxxx or Pxxxxxxxx
            new PIIPattern(
                PIIEntity.Type.PASSPORT,
                Pattern.compile("(?<![A-Za-z])[GP]\\d{8}(?![\\dA-Za-z])", Pattern.CASE_INSENSITIVE),
                0.9
            ),

            // Chinese social credit code: 18 chars
            new PIIPattern(
                PIIEntity.Type.SOCIAL_CREDIT,
                Pattern.compile("(?<![A-Za-z0-9])[0-9A-HJ-NP-QRTUWXY]{2}\\d{6}[0-9A-HJ-NP-QRTUWXY]{10}(?![A-Za-z0-9])"),
                0.9
            ),

            // Chinese license plate
            new PIIPattern(
                PIIEntity.Type.LICENSE_PLATE,
                Pattern.compile("[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-Z][A-HJ-NP-Z0-9]{5,6}"),
                0.9
            ),

            // Email
            new PIIPattern(
                PIIEntity.Type.EMAIL,
                Pattern.compile("[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}"),
                0.95
            ),

            // IPv4
            new PIIPattern(
                PIIEntity.Type.IP_ADDRESS,
                Pattern.compile("(?<!\\d)(?:\\d{1,3}\\.){3}\\d{1,3}(?!\\d)"),
                0.8
            )
        );
    }

    /**
     * Internal class for PII pattern.
     */
    private static record PIIPattern(
        PIIEntity.Type type,
        Pattern pattern,
        double confidence
    ) {}
}
