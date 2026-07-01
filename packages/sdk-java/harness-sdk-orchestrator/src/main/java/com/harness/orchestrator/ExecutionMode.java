package com.harness.orchestrator;

/**
 * Step execution mode.
 */
public enum ExecutionMode {
    SEQUENTIAL("sequential"),
    PARALLEL("parallel"),
    CONDITIONAL("conditional");

    private final String value;

    ExecutionMode(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }

    public static ExecutionMode fromValue(String value) {
        for (ExecutionMode mode : values()) {
            if (mode.value.equalsIgnoreCase(value)) {
                return mode;
            }
        }
        return SEQUENTIAL;
    }
}
