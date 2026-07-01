package com.harness.orchestrator;

/**
 * Workflow step execution status.
 */
public enum StepStatus {
    PENDING("pending"),
    RUNNING("running"),
    SUCCESS("success"),
    FAILED("failed"),
    SKIPPED("skipped");

    private final String value;

    StepStatus(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }

    public static StepStatus fromValue(String value) {
        for (StepStatus status : values()) {
            if (status.value.equalsIgnoreCase(value)) {
                return status;
            }
        }
        return PENDING;
    }
}
