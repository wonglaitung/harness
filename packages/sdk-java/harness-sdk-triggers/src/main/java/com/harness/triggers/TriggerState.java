package com.harness.triggers;

/**
 * States a trigger can be in.
 *
 * <p>Triggers transition between these states during their lifecycle.</p>
 */
public enum TriggerState {
    /** Not started yet */
    IDLE("idle"),
    /** Active and waiting for trigger condition */
    RUNNING("running"),
    /** Temporarily paused */
    PAUSED("paused"),
    /** Permanently stopped */
    STOPPED("stopped"),
    /** Error state */
    ERROR("error");

    private final String value;

    TriggerState(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }
}
