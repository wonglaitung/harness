package com.harness.loop.automation;

/**
 * Status of an Automation.
 *
 * <p>Automations transition through these states during their lifecycle:</p>
 * <ul>
 *   <li>PENDING - Not started yet</li>
 *   <li>RUNNING - Active and monitoring</li>
 *   <li>PAUSED - Temporarily paused</li>
 *   <li>STOPPED - Permanently stopped</li>
 *   <li>ERROR - Error state</li>
 * </ul>
 */
public enum AutomationStatus {
    PENDING("pending"),
    RUNNING("running"),
    PAUSED("paused"),
    STOPPED("stopped"),
    ERROR("error");

    private final String value;

    AutomationStatus(String value) {
        this.value = value;
    }

    public String getValue() {
        return value;
    }

    public static AutomationStatus fromValue(String value) {
        for (AutomationStatus status : values()) {
            if (status.value.equalsIgnoreCase(value)) {
                return status;
            }
        }
        return PENDING;
    }
}
