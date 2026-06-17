package com.harness.types;

/**
 * Stop reason for LLM response.
 */
public enum StopReason {
    END_TURN("end_turn"),
    TOOL_USE("tool_use"),
    MAX_TOKENS("max_tokens"),
    STOP_SEQUENCE("stop_sequence");

    private final String value;

    StopReason(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }

    public static StopReason fromValue(String value) {
        for (StopReason reason : values()) {
            if (reason.value.equals(value)) {
                return reason;
            }
        }
        return END_TURN; // Default
    }
}