package com.harness.gate.models;

import java.util.List;
import java.util.Map;

/**
 * A single issue found by a gate validator.
 */
public record GateFinding(
        String id,
        FindingType type,
        GateSeverity severity,
        String message,
        String field,
        String evidence) {

    public GateFinding(String id, FindingType type, GateSeverity severity, String message) {
        this(id, type, severity, message, null, null);
    }

    public Map<String, Object> asDict() {
        Map<String, Object> m = new java.util.LinkedHashMap<>();
        m.put("id", id);
        m.put("type", type.value());
        m.put("severity", severity.value());
        m.put("message", message);
        m.put("field", field);
        m.put("evidence", evidence);
        return m;
    }
}
