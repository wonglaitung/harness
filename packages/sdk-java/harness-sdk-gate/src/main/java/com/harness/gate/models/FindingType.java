package com.harness.gate.models;

/**
 * Which validator produced a finding.
 */
public enum FindingType {
    FORMAT("format"),
    FACT("fact"),
    LOGIC("logic"),
    RECONCILIATION("reconciliation");

    private final String value;

    FindingType(String value) {
        this.value = value;
    }

    public String value() {
        return value;
    }
}
