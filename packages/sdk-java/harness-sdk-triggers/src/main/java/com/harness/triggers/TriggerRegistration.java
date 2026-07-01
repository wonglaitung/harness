package com.harness.triggers;

import java.time.Instant;

/**
 * Registration information for a trigger.
 *
 * <p>Tracks the trigger, its action, and execution statistics.</p>
 */
public class TriggerRegistration {
    private final Trigger trigger;
    private final TriggerAction action;
    private volatile boolean enabled;

    // Statistics
    private volatile Instant lastFired;
    private volatile int fireCount;
    private volatile int errorCount;
    private volatile String lastError;

    public TriggerRegistration(Trigger trigger, TriggerAction action) {
        this(trigger, action, true);
    }

    public TriggerRegistration(Trigger trigger, TriggerAction action, boolean enabled) {
        this.trigger = trigger;
        this.action = action;
        this.enabled = enabled;
    }

    public Trigger getTrigger() {
        return trigger;
    }

    public TriggerAction getAction() {
        return action;
    }

    public boolean isEnabled() {
        return enabled;
    }

    public void setEnabled(boolean enabled) {
        this.enabled = enabled;
    }

    public Instant getLastFired() {
        return lastFired;
    }

    public void setLastFired(Instant lastFired) {
        this.lastFired = lastFired;
    }

    public int getFireCount() {
        return fireCount;
    }

    public void incrementFireCount() {
        this.fireCount++;
    }

    public int getErrorCount() {
        return errorCount;
    }

    public void incrementErrorCount() {
        this.errorCount++;
    }

    public String getLastError() {
        return lastError;
    }

    public void setLastError(String lastError) {
        this.lastError = lastError;
    }
}
