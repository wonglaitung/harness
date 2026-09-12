package com.harness.gate;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * C3: Logic reconciler — cross-field business rule validation.
 *
 * <p>Supports declarative rules:
 * <ul>
 *   <li>{@code numeric_sum}: numeric_field = numeric_field_1 + numeric_field_2 + ...</li>
 *   <li>{@code equality}: field_a == field_b</li>
 *   <li>{@code range}: field in [min, max]</li>
 * </ul>
 */
public class LogicReconciler {

    /**
     * A declarative business rule.
     *
     * @param type   rule type (numeric_sum, equality, range)
     * @param field  the field being checked
     * @param params rule-specific parameters
     */
    public record RuleSpec(String type, String field, Map<String, Object> params) {}

    /**
     * Validate content against declarative rules.
     *
     * @param content the content to check
     * @param rules   the declarative rules to apply
     * @return list of findings (empty = all rules satisfied)
     */
    public List<GateFinding> reconcile(String content, List<RuleSpec> rules) {
        List<GateFinding> findings = new ArrayList<>();

        if (content == null || content.isBlank() || rules == null || rules.isEmpty()) {
            return findings;
        }

        for (RuleSpec rule : rules) {
            switch (rule.type()) {
                case "numeric_sum" -> checkNumericSum(content, rule, findings);
                case "equality" -> checkEquality(content, rule, findings);
                case "range" -> checkRange(content, rule, findings);
                default -> findings.add(new GateFinding(
                    "logic:unknown-rule", FindingType.LOGIC, GateSeverity.WARNING,
                    "Unknown rule type: " + rule.type(), ""));
            }
        }

        return findings;
    }

    /**
     * Check that a numeric field equals the sum of specified components.
     * Params: components (List<String>) — field names to sum.
     */
    @SuppressWarnings("unchecked")
    private void checkNumericSum(String content, RuleSpec rule, List<GateFinding> findings) {
        List<String> components = (List<String>) rule.params().get("components");
        if (components == null || components.isEmpty()) return;

        Pattern totalPattern = Pattern.compile(
            Pattern.quote(rule.field()) + "\\s*[:：=]\\s*([\\d,]+(?:\\.\\d+)?)",
            Pattern.CASE_INSENSITIVE);
        Matcher totalMatcher = totalPattern.matcher(content);
        if (!totalMatcher.find()) return;

        double total = parseNumber(totalMatcher.group(1));
        double sum = 0;

        for (String comp : components) {
            Pattern compPattern = Pattern.compile(
                Pattern.quote(comp) + "\\s*[:：=]\\s*([\\d,]+(?:\\.\\d+)?)",
                Pattern.CASE_INSENSITIVE);
            Matcher compMatcher = compPattern.matcher(content);
            if (compMatcher.find()) {
                sum += parseNumber(compMatcher.group(1));
            }
        }

        if (Math.abs(total - sum) > 0.01) {
            findings.add(new GateFinding(
                "logic:sum-mismatch", FindingType.LOGIC, GateSeverity.ERROR,
                rule.field() + " = " + total + " but sum of components = " + sum,
                "components: " + String.join(", ", components)));
        }
    }

    /**
     * Check that two fields are equal.
     * Params: expected (String) — the field that should match.
     */
    private void checkEquality(String content, RuleSpec rule, List<GateFinding> findings) {
        String expected = (String) rule.params().get("expected");
        if (expected == null) return;

        Pattern fieldPattern = Pattern.compile(
            Pattern.quote(rule.field()) + "\\s*[:：=]\\s*(.+?)(?:\\n|$)",
            Pattern.CASE_INSENSITIVE);
        Pattern expectedPattern = Pattern.compile(
            Pattern.quote(expected) + "\\s*[:：=]\\s*(.+?)(?:\\n|$)",
            Pattern.CASE_INSENSITIVE);

        Matcher fm = fieldPattern.matcher(content);
        Matcher em = expectedPattern.matcher(content);

        if (fm.find() && em.find()) {
            String fieldVal = fm.group(1).trim();
            String expectedVal = em.group(1).trim();
            if (!fieldVal.equals(expectedVal)) {
                findings.add(new GateFinding(
                    "logic:inequality", FindingType.LOGIC, GateSeverity.ERROR,
                    rule.field() + " = " + fieldVal + " but " + expected + " = " + expectedVal,
                    ""));
            }
        }
    }

    /**
     * Check that a field value is within [min, max].
     * Params: min (Double), max (Double).
     */
    private void checkRange(String content, RuleSpec rule, List<GateFinding> findings) {
        Number min = (Number) rule.params().get("min");
        Number max = (Number) rule.params().get("max");
        if (min == null || max == null) return;

        Pattern pattern = Pattern.compile(
            Pattern.quote(rule.field()) + "\\s*[:：=]\\s*([\\d,]+(?:\\.\\d+)?)",
            Pattern.CASE_INSENSITIVE);
        Matcher matcher = pattern.matcher(content);
        if (!matcher.find()) return;

        double value = parseNumber(matcher.group(1));
        if (value < min.doubleValue() || value > max.doubleValue()) {
            findings.add(new GateFinding(
                "logic:out-of-range", FindingType.LOGIC, GateSeverity.ERROR,
                rule.field() + " = " + value + " outside [" + min + ", " + max + "]",
                ""));
        }
    }

    private static double parseNumber(String s) {
        if (s == null) return 0;
        return Double.parseDouble(s.replace(",", ""));
    }
}
