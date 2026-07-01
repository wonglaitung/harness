package com.harness.orchestrator;

/**
 * Workflow execution status.
 */
public enum WorkflowStatus {
    PENDING("pending"),
    RUNNING("running"),
    COMPLETED("completed"),
    FAILED("failed"),
    CANCELLED("cancelled");

    private final String value;

    WorkflowStatus(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }

    public static WorkflowStatus fromValue(String value) {
        for (WorkflowStatus status : values()) {
            if (status.value.equalsIgnoreCase(value)) {
                return status;
            }
        }
        return PENDING;
    }
}
