package com.harness.gate.declarative;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.harness.gate.GateRule;
import com.harness.gate.models.FindingType;
import com.harness.gate.models.GateFinding;
import com.harness.gate.models.GateSeverity;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Declarative business-rule specs for the deterministic gate.
 *
 * <p>Compile a list of spec maps into {@link GateRule} callables — the exact
 * contract {@code LogicReconciler} consumes. Lets operators author invariants
 * (e.g. a numeric-sum tie-out) in JSON without writing Java.</p>
 *
 * <p>IMPORTANT: declarative specs only see the delivery *text*. Checks needing an
 * external deterministic master source must be expressed as a Java
 * {@link GateRule} instead — the declarative engine has no access to that
 * context. Both paths feed the same {@code LogicReconciler(rules=...)}.</p>
 */
public final class RuleCompiler {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private static final Map<String, Function<Map<String, Object>, GateRule>> DISPATCH =
            Map.of(
                    "numeric_sum", RuleCompiler::numericSumRule,
                    "equality", RuleCompiler::equalityRule,
                    "range", RuleCompiler::rangeRule,
                    "regex_present", RuleCompiler::regexPresentRule);

    private RuleCompiler() {
    }

    private static GateSeverity severityOf(Map<String, Object> spec) {
        Object s = spec.get("severity");
        // Python default: missing severity == "error" (i.e. ERROR); only explicit "warning" downgrades.
        return (s == null || "error".equals(s)) ? GateSeverity.ERROR : GateSeverity.WARNING;
    }

    private static String str(Object o, String dflt) {
        return o == null ? dflt : o.toString();
    }

    private static double f4(double v) {
        return Math.round(v * 1e4) / 1e4;
    }

    private static Double toNumber(Object raw) {
        if (raw instanceof Number n) {
            return n.doubleValue();
        }
        if (raw == null) {
            return null;
        }
        String s = raw.toString().replace(",", "").replace("%", "");
        for (String unit : new String[]{"亿元", "万元", "元", "USD", "$"}) {
            s = s.replace(unit, "");
        }
        s = s.strip();
        try {
            return Double.parseDouble(s);
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private static Double extractLabeledNumber(String text, String label) {
        if (text == null) {
            return null;
        }
        Pattern pat = Pattern.compile(
                Pattern.quote(label) + "[:：\\s]+[¥$]?\\s?([\\d][\\d,]*(?:\\.\\d+)?)");
        Matcher m = pat.matcher(text);
        if (m.find()) {
            return toNumber(m.group(1));
        }
        return null;
    }

    private static Map<String, Object> valuesFromContent(String content) {
        if (content == null) {
            return null;
        }
        try {
            Object o = MAPPER.readValue(content, Object.class);
            if (o instanceof Map) {
                @SuppressWarnings("unchecked")
                Map<String, Object> m = (Map<String, Object>) o;
                return m;
            }
        } catch (IOException e) {
            // not valid JSON -> treat as free text
        }
        return null;
    }

    private static Double lookup(String key, String content, Map<String, Object> data) {
        if (data != null) {
            Object v = data.get(key);
            if (v instanceof Number n) {
                return n.doubleValue();
            }
        }
        return extractLabeledNumber(content, key);
    }

    private static GateRule numericSumRule(Map<String, Object> spec) {
        String rid = str(spec.get("id"), "numeric_sum");
        String left = (String) spec.get("left");
        @SuppressWarnings("unchecked")
        List<String> rights = (List<String>) spec.get("rights");
        double tol = spec.get("tolerance") instanceof Number
                ? ((Number) spec.get("tolerance")).doubleValue() : 0.01;
        GateSeverity sev = severityOf(spec);
        String msg = str(spec.get("message"),
                left + " 应≈ Σ" + rights + "（容差 " + (int) (tol * 100) + "%）");
        return (content, sources) -> {
            List<GateFinding> fs = new ArrayList<>();
            Map<String, Object> data = valuesFromContent(content);
            Double lv = lookup(left, content, data);
            List<Double> rv = new ArrayList<>();
            for (String r : rights) {
                Double v = lookup(r, content, data);
                if (v != null) {
                    rv.add(v);
                }
            }
            if (lv == null || rv.isEmpty()) {
                fs.add(new GateFinding("logic:" + rid + ":missing", FindingType.LOGIC,
                        GateSeverity.WARNING, rid + ": 无法取数（" + left + " 或 " + rights + "）"));
                return fs;
            }
            double s = rv.stream().mapToDouble(Double::doubleValue).sum();
            if (Math.abs(lv - s) / Math.max(Math.abs(lv), 1e-9) > tol) {
                double dev = Math.abs(lv - s) / Math.max(Math.abs(lv), 1e-9);
                fs.add(new GateFinding("logic:" + rid, FindingType.LOGIC, sev,
                        msg + "：" + left + "=" + f4(lv) + ", Σ" + rights + "=" + f4(s)
                                + ", 偏差 " + String.format("%.2f%%", dev * 100)));
            }
            return fs;
        };
    }

    private static GateRule equalityRule(Map<String, Object> spec) {
        String rid = str(spec.get("id"), "equality");
        String left = (String) spec.get("left");
        String right = (String) spec.get("right");
        GateSeverity sev = severityOf(spec);
        String msg = str(spec.get("message"), left + " 应= " + right);
        return (content, sources) -> {
            Map<String, Object> data = valuesFromContent(content);
            Double lv = lookup(left, content, data);
            Double rv = lookup(right, content, data);
            if (lv == null || rv == null) {
                return List.of(new GateFinding("logic:" + rid + ":missing", FindingType.LOGIC,
                        GateSeverity.WARNING, rid + ": 无法取数（" + left + " 或 " + right + "）"));
            }
            if (Math.abs(lv - rv) / Math.max(Math.abs(lv), 1e-9) > 1e-9) {
                return List.of(new GateFinding("logic:" + rid, FindingType.LOGIC, sev,
                        msg + "：" + left + "=" + f4(lv) + ", " + right + "=" + f4(rv)));
            }
            return List.of();
        };
    }

    private static GateRule rangeRule(Map<String, Object> spec) {
        String rid = str(spec.get("id"), "range");
        String field = (String) spec.get("field");
        Object lo = spec.get("min");
        Object hi = spec.get("max");
        GateSeverity sev = severityOf(spec);
        String msg = str(spec.get("message"), field + " 应在 [" + lo + ", " + hi + "] 内");
        Double loD = lo instanceof Number ? ((Number) lo).doubleValue() : null;
        Double hiD = hi instanceof Number ? ((Number) hi).doubleValue() : null;
        return (content, sources) -> {
            Map<String, Object> data = valuesFromContent(content);
            Double v = lookup(field, content, data);
            if (v == null) {
                return List.of(new GateFinding("logic:" + rid + ":missing", FindingType.LOGIC,
                        GateSeverity.WARNING, rid + ": 无法取数（" + field + "）"));
            }
            if ((loD != null && v < loD) || (hiD != null && v > hiD)) {
                return List.of(new GateFinding("logic:" + rid, FindingType.LOGIC, sev,
                        msg + "：" + field + "=" + f4(v)));
            }
            return List.of();
        };
    }

    private static GateRule regexPresentRule(Map<String, Object> spec) {
        String rid = str(spec.get("id"), "regex_present");
        String pattern = (String) spec.get("pattern");
        GateSeverity sev = severityOf(spec);
        String msg = str(spec.get("message"), "交付必须包含匹配 /" + pattern + "/ 的内容");
        Pattern compiled = Pattern.compile(pattern);
        return (content, sources) -> {
            if (!compiled.matcher(content == null ? "" : content).find()) {
                return List.of(new GateFinding("logic:" + rid, FindingType.LOGIC, sev, msg));
            }
            return List.of();
        };
    }

    /**
     * Compile declarative rule specs into {@link GateRule} callables.
     *
     * @throws IllegalArgumentException on an unknown {@code kind} or missing {@code kind}.
     */
    public static List<GateRule> compileRuleSpecs(List<Map<String, Object>> specs) {
        List<GateRule> rules = new ArrayList<>();
        if (specs == null) {
            return rules;
        }
        for (Map<String, Object> spec : specs) {
            Object kind = spec.get("kind");
            if (kind == null) {
                throw new IllegalArgumentException("rule spec missing 'kind'");
            }
            Function<Map<String, Object>, GateRule> factory = DISPATCH.get(kind.toString());
            if (factory == null) {
                throw new IllegalArgumentException(
                        "Unknown rule kind: " + kind + " (expected one of " + DISPATCH.keySet() + ")");
            }
            rules.add(factory.apply(spec));
        }
        return rules;
    }

    /**
     * Load declarative rule specs from a JSON file. Accepts either a bare list or
     * {@code {"rules": [...]}}. YAML is not supported in the Java port (no YAML
     * dependency); use JSON.
     */
    public static List<Map<String, Object>> loadRuleSpecs(String path) throws IOException {
        String text = Files.readString(Path.of(path), java.nio.charset.StandardCharsets.UTF_8);
        Object data;
        if (path.endsWith(".yaml") || path.endsWith(".yml")) {
            throw new UnsupportedOperationException(
                    "YAML rule specs are not supported in the Java port; use JSON");
        }
        data = MAPPER.readValue(text, Object.class);
        if (data instanceof Map) {
            @SuppressWarnings("unchecked")
            Map<String, Object> m = (Map<String, Object>) data;
            if (m.containsKey("rules")) {
                data = m.get("rules");
            }
        }
        if (data instanceof List) {
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> list = (List<Map<String, Object>>) data;
            return list;
        }
        throw new IllegalArgumentException("rule specs must be a list or {'rules': [...]}");
    }
}
