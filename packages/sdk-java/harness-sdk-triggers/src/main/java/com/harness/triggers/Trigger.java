package com.harness.triggers;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;

/**
 * Abstract base class for triggers.
 *
 * <p>A Trigger monitors for a specific condition and fires events when
 * that condition is met. Subclasses implement specific triggering
 * mechanisms (cron, interval, webhook, etc.).</p>
 *
 * <h2>Lifecycle</h2>
 * <ol>
 *   <li>Create trigger with configuration</li>
 *   <li>Call start() with a callback function</li>
 *   <li>Trigger monitors for condition</li>
 *   <li>When condition met, creates TriggerEvent and calls callback</li>
 *   <li>Call stop() to cease monitoring</li>
 * </ol>
 */
public abstract class Trigger {
    protected final TriggerType triggerType;
    protected String id;
    protected TriggerState state = TriggerState.IDLE;
    protected TriggerAction action;
    protected String lastError;

    /**
     * Create a new Trigger.
     *
     * @param triggerType The type of this trigger
     */
    protected Trigger(TriggerType triggerType) {
        this.triggerType = triggerType;
        this.id = generateId();
    }

    /**
     * Start the trigger.
     *
     * @param callback Function to call when trigger fires
     * @return CompletableFuture that completes when started
     */
    public abstract CompletableFuture<Void> start(Consumer<TriggerEvent> callback);

    /**
     * Stop the trigger.
     *
     * @return CompletableFuture that completes when stopped
     */
    public abstract CompletableFuture<Void> stop();

    /**
     * Create a trigger event.
     *
     * @param payload Optional data to include in the event
     * @return TriggerEvent instance
     */
    public TriggerEvent createEvent(Map<String, Object> payload) {
        return createEvent(payload, new HashMap<>());
    }

    /**
     * Create a trigger event with routing metadata.
     *
     * @param payload Optional data to include in the event
     * @param routingMetadata Metadata for routing responses
     * @return TriggerEvent instance
     */
    public TriggerEvent createEvent(Map<String, Object> payload, Map<String, Object> routingMetadata) {
        return new TriggerEvent.Builder()
                .triggerType(triggerType)
                .triggerId(id)
                .payload(payload != null ? payload : new HashMap<>())
                .routingMetadata(routingMetadata != null ? routingMetadata : new HashMap<>())
                .build();
    }

    /**
     * Check if trigger is currently running.
     */
    public boolean isRunning() {
        return state == TriggerState.RUNNING;
    }

    /**
     * Check if trigger is stopped.
     */
    public boolean isStopped() {
        return state == TriggerState.STOPPED;
    }

    /**
     * Get the trigger type.
     */
    public TriggerType getTriggerType() {
        return triggerType;
    }

    /**
     * Get the trigger ID.
     */
    public String getId() {
        return id;
    }

    /**
     * Set the trigger ID.
     */
    public void setId(String id) {
        this.id = id;
    }

    /**
     * Get the trigger state.
     */
    public TriggerState getState() {
        return state;
    }

    /**
     * Get the action.
     */
    public TriggerAction getAction() {
        return action;
    }

    /**
     * Set the action.
     */
    public void setAction(TriggerAction action) {
        this.action = action;
    }

    /**
     * Get the last error.
     */
    public String getLastError() {
        return lastError;
    }

    /**
     * Set state to running.
     */
    protected void setRunning() {
        this.state = TriggerState.RUNNING;
    }

    /**
     * Set state to stopped.
     */
    protected void setStopped() {
        this.state = TriggerState.STOPPED;
    }

    /**
     * Set state to error.
     */
    protected void setError(String error) {
        this.state = TriggerState.ERROR;
        this.lastError = error;
    }

    /**
     * Generate a unique trigger ID.
     */
    protected String generateId() {
        return triggerType.getValue() + "_" + UUID.randomUUID().toString().substring(0, 8);
    }

    @Override
    public String toString() {
        return getClass().getSimpleName() + "{id='" + id + "', state=" + state.getValue() + "}";
    }
}
