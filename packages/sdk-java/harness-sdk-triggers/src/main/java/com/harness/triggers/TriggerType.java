package com.harness.triggers;

/**
 * Types of triggers.
 *
 * <p>Each type defines a different way to trigger goal execution.</p>
 */
public enum TriggerType {
    /** Cron expression scheduling */
    CRON("cron"),
    /** Fixed interval scheduling */
    INTERVAL("interval"),
    /** HTTP webhook trigger */
    WEBHOOK("webhook"),
    /** Periodic heartbeat check */
    HEARTBEAT("heartbeat"),
    /** File system changes */
    FILE_WATCH("file_watch"),
    /** Event bus subscription */
    EVENT("event");

    private final String value;

    TriggerType(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }

    public static TriggerType fromValue(String value) {
        for (TriggerType type : values()) {
            if (type.value.equalsIgnoreCase(value)) {
                return type;
            }
        }
        return EVENT;
    }
}
