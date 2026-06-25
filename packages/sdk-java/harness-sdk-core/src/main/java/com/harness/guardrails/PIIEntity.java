package com.harness.guardrails;

import java.util.Map;
import java.util.regex.MatchResult;

/**
 * PII entity detected in text.
 */
public class PIIEntity {

    public enum Type {
        PHONE("phone", "手机号"),
        ID_CARD("id_card", "身份证号"),
        BANK_CARD("bank_card", "银行卡号"),
        PASSPORT("passport", "护照号"),
        EMAIL("email", "邮箱"),
        IP_ADDRESS("ip_address", "IP地址"),
        SOCIAL_CREDIT("social_credit", "社会信用代码"),
        LICENSE_PLATE("license_plate", "车牌号"),
        NAME("name", "姓名");

        private final String code;
        private final String description;

        Type(String code, String description) {
            this.code = code;
            this.description = description;
        }

        public String getCode() { return code; }
        public String getDescription() { return description; }
    }

    private final Type type;
    private final String value;
    private final int start;
    private final int end;
    private final double confidence;
    private final Map<String, Object> metadata;

    public PIIEntity(Type type, String value, int start, int end, double confidence) {
        this(type, value, start, end, confidence, Map.of());
    }

    public PIIEntity(Type type, String value, int start, int end, double confidence, Map<String, Object> metadata) {
        this.type = type;
        this.value = value;
        this.start = start;
        this.end = end;
        this.confidence = confidence;
        this.metadata = metadata;
    }

    public Type getType() { return type; }
    public String getValue() { return value; }
    public int getStart() { return start; }
    public int getEnd() { return end; }
    public double getConfidence() { return confidence; }
    public Map<String, Object> getMetadata() { return metadata; }

    /**
     * Redact the entity in the given text.
     */
    public String redact(String text, String mask) {
        if (start < 0 || end > text.length()) {
            return text;
        }
        return text.substring(0, start) + mask + text.substring(end);
    }

    /**
     * Redact with default mask.
     */
    public String redact(String text) {
        return redact(text, "[REDACTED_" + type.getCode().toUpperCase() + "]");
    }

    @Override
    public String toString() {
        return String.format("PIIEntity{type=%s, value='%s', start=%d, end=%d, confidence=%.2f}",
            type, value, start, end, confidence);
    }
}
