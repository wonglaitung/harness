package com.harness.types;

/**
 * Agent loop state machine states.
 */
public enum LoopState {
    IDLE("idle"),
    BUILDING_CONTEXT("building"),
    CALLING_LLM("calling"),
    PARSING_RESPONSE("parsing"),
    EXECUTING_TOOLS("executing"),
    COMPLETED("completed"),
    ERROR("error"),
    INTERRUPTED("interrupted"),
    STUCK("stuck"),
    MAX_ITERATIONS("max_iterations");

    private final String value;

    LoopState(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }

    public static LoopState fromValue(String value) {
        for (LoopState state : values()) {
            if (state.value.equals(value)) {
                return state;
            }
        }
        return IDLE;
    }
}