package com.harness.gate.models;

/**
 * Severity of a gate finding.
 */
public enum GateSeverity {
    INFO("info"),
    WARNING("warning"),
    ERROR("error");

    private final String value;

    GateSeverity(String value) {
        this.value = value;
    }

    public String value() {
        return value;
    }
}
