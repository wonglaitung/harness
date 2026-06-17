package com.harness.security;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Result sanitizer.
 *
 * Removes sensitive information from tool outputs before
 * returning to the LLM.
 */
public class ResultSanitizer {

    private static final Logger logger = LoggerFactory.getLogger(ResultSanitizer.class);

    /**
     * Default sanitization rules.
     */
    public static final List<SanitizationRule> DEFAULT_RULES = List.of(
        SanitizationRule.of("api_key",
            "(api[_-]?key[\"\\s:=]+)[\"']?[\\w-]{20,}[\"']?",
            "$1[REDACTED]",
            "API Key"),
        SanitizationRule.of("password",
            "(password[\"\\s:=]+)[\"']?[^\\s\"']{8,}[\"']?",
            "$1[REDACTED]",
            "Password"),
        SanitizationRule.of("aws_key",
            "AKIA[0-9A-Z]{16}",
            "AKIA[REDACTED]",
            "AWS Access Key"),
        SanitizationRule.of("secret_key",
            "(secret[_-]?key[\"\\s:=]+)[\"']?[\\w-]{20,}[\"']?",
            "$1[REDACTED]",
            "Secret Key"),
        SanitizationRule.of("token",
            "(token[\"\\s:=]+)[\"']?[\\w-]{20,}[\"']?",
            "$1[REDACTED]",
            "Token"),
        SanitizationRule.of("private_key",
            "-----BEGIN (?:RSA |EC )?PRIVATE KEY-----",
            "-----BEGIN PRIVATE KEY [REDACTED]-----",
            "Private Key"),
        SanitizationRule.of("email",
            "\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b",
            "[EMAIL REDACTED]",
            "Email Address"),
        SanitizationRule.of("credit_card",
            "\\b\\d{4}[-\\s]?\\d{4}[-\\s]?\\d{4}[-\\s]?\\d{4}\\b",
            "[CARD REDACTED]",
            "Credit Card"),
        SanitizationRule.of("phone",
            "\\b\\d{3}[-.\\s]?\\d{3}[-.\\s]?\\d{4}\\b",
            "[PHONE REDACTED]",
            "Phone Number"),
        SanitizationRule.of("ssn",
            "\\b\\d{3}-\\d{2}-\\d{4}\\b",
            "[SSN REDACTED]",
            "Social Security Number")
    );

    /**
     * Default maximum length.
     */
    public static final int DEFAULT_MAX_LENGTH = 100_000;

    private final List<SanitizationRule> rules;
    private final int maxLength;
    private final boolean enabled;

    /**
     * Create sanitizer with default settings.
     */
    public ResultSanitizer() {
        this(new ArrayList<>(DEFAULT_RULES), DEFAULT_MAX_LENGTH, true);
    }

    /**
     * Create sanitizer with custom settings.
     *
     * @param rules sanitization rules
     * @param maxLength maximum output length
     * @param enabled whether sanitization is enabled
     */
    public ResultSanitizer(List<SanitizationRule> rules, int maxLength, boolean enabled) {
        this.rules = rules;
        this.maxLength = maxLength;
        this.enabled = enabled;
    }

    /**
     * Sanitize content.
     *
     * @param content content to sanitize
     * @return sanitized content
     */
    public String sanitize(String content) {
        if (!enabled) {
            return content;
        }

        String result = content;

        // Apply all rules
        for (SanitizationRule rule : rules) {
            result = rule.pattern().matcher(result).replaceAll(rule.replacement());
        }

        // Truncate if too long
        if (result.length() > maxLength) {
            int headLength = maxLength / 2;
            int tailLength = maxLength / 4;
            String head = result.substring(0, headLength);
            String tail = result.substring(result.length() - tailLength);
            result = head + "\n\n... [截断] ...\n\n" + tail;
        }

        return result;
    }

    /**
     * Get report of what was redacted.
     *
     * @param original original content
     * @return redaction report
     */
    public RedactionReport getRedactionReport(String original) {
        List<RedactionInfo> redactions = new ArrayList<>();

        for (SanitizationRule rule : rules) {
            java.util.regex.Matcher matcher = rule.pattern().matcher(original);
            int count = 0;
            while (matcher.find()) {
                count++;
            }
            if (count > 0) {
                redactions.add(new RedactionInfo(rule.name(), rule.description(), count));
            }
        }

        int totalRedactions = redactions.stream()
            .mapToInt(RedactionInfo::count)
            .sum();

        return new RedactionReport(redactions, totalRedactions);
    }

    /**
     * Add a custom rule.
     */
    public void addRule(SanitizationRule rule) {
        rules.add(rule);
    }

    /**
     * Remove a rule by name.
     *
     * @return true if rule was removed
     */
    public boolean removeRule(String name) {
        for (int i = 0; i < rules.size(); i++) {
            if (rules.get(i).name().equals(name)) {
                rules.remove(i);
                return true;
            }
        }
        return false;
    }

    /**
     * Sanitize dictionary values.
     */
    public Map<String, Object> sanitizeMap(Map<String, Object> data) {
        Map<String, Object> result = new java.util.HashMap<>();
        for (Map.Entry<String, Object> entry : data.entrySet()) {
            Object value = entry.getValue();
            if (value instanceof String) {
                result.put(entry.getKey(), sanitize((String) value));
            } else if (value instanceof Map) {
                @SuppressWarnings("unchecked")
                Map<String, Object> nested = (Map<String, Object>) value;
                result.put(entry.getKey(), sanitizeMap(nested));
            } else if (value instanceof List) {
                @SuppressWarnings("unchecked")
                List<Object> list = (List<Object>) value;
                List<Object> sanitizedList = new ArrayList<>();
                for (Object item : list) {
                    if (item instanceof String) {
                        sanitizedList.add(sanitize((String) item));
                    } else {
                        sanitizedList.add(item);
                    }
                }
                result.put(entry.getKey(), sanitizedList);
            } else {
                result.put(entry.getKey(), value);
            }
        }
        return result;
    }

    /**
     * Quick sanitize function.
     */
    public static String sanitizeOutput(String content) {
        return new ResultSanitizer().sanitize(content);
    }

    /**
     * Redaction info for a single rule.
     */
    public record RedactionInfo(String rule, String description, int count) {
    }

    /**
     * Redaction report.
     */
    public record RedactionReport(List<RedactionInfo> redactions, int totalRedactions) {
    }
}