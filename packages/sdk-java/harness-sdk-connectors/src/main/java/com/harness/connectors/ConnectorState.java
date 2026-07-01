package com.harness.connectors;

/**
 * Connector lifecycle state.
 */
public enum ConnectorState {
    IDLE("idle"),
    RUNNING("running"),
    STOPPED("stopped"),
    ERROR("error");

    private final String value;

    ConnectorState(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }

    public static ConnectorState fromValue(String value) {
        for (ConnectorState state : values()) {
            if (state.value.equalsIgnoreCase(value)) {
                return state;
            }
        }
        return IDLE;
    }
}
