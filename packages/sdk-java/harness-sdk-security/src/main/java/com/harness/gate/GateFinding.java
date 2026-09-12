package com.harness.gate;

import java.util.Map;

/**
 * A single finding from a gate validator.
 *
 * @param id       unique finding identifier (e.g., "fmt:empty", "fact:no-source")
 * @param type     finding category
 * @param severity finding severity (ERROR blocks delivery, WARNING is advisory)
 * @param message  human-readable description
 * @param evidence supporting evidence (optional)
 */
public record GateFinding(
    String id,
    FindingType type,
    GateSeverity severity,
    String message,
    String evidence
) {
    public Map<String, Object> asDict() {
        return Map.of(
            "id", id,
            "type", type.name(),
            "severity", severity.name(),
            "message", message,
            "evidence", evidence != null ? evidence : ""
        );
    }
}
