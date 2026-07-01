package com.harness.triggers;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;

/**
 * Event created when a trigger fires.
 *
 * <p>Contains metadata about the trigger and optional payload data.</p>
 */
public class TriggerEvent {
    private final TriggerType triggerType;
    private final String triggerId;
    private final Instant timestamp;
    private final Map<String, Object> payload;
    private final Map<String, Object> routingMetadata;

    private TriggerEvent(Builder builder) {
        this.triggerType = builder.triggerType;
        this.triggerId = builder.triggerId;
        this.timestamp = builder.timestamp != null ? builder.timestamp : Instant.now();
        this.payload = builder.payload;
        this.routingMetadata = builder.routingMetadata;
    }

    public TriggerType getTriggerType() {
        return triggerType;
    }

    public String getTriggerId() {
        return triggerId;
    }

    public Instant getTimestamp() {
        return timestamp;
    }

    public Map<String, Object> getPayload() {
        return payload;
    }

    public Map<String, Object> getRoutingMetadata() {
        return routingMetadata;
    }

    /**
     * Check if this is a scheduled event (cron/interval).
     */
    public boolean isScheduled() {
        return triggerType == TriggerType.CRON || triggerType == TriggerType.INTERVAL;
    }

    /**
     * Check if this is an external event (webhook/event).
     */
    public boolean isExternal() {
        return triggerType == TriggerType.WEBHOOK || triggerType == TriggerType.EVENT;
    }

    public static class Builder {
        private TriggerType triggerType;
        private String triggerId;
        private Instant timestamp;
        private Map<String, Object> payload = new HashMap<>();
        private Map<String, Object> routingMetadata = new HashMap<>();

        public Builder triggerType(TriggerType triggerType) {
            this.triggerType = triggerType;
            return this;
        }

        public Builder triggerId(String triggerId) {
            this.triggerId = triggerId;
            return this;
        }

        public Builder timestamp(Instant timestamp) {
            this.timestamp = timestamp;
            return this;
        }

        public Builder payload(Map<String, Object> payload) {
            this.payload = payload != null ? new HashMap<>(payload) : new HashMap<>();
            return this;
        }

        public Builder addPayload(String key, Object value) {
            this.payload.put(key, value);
            return this;
        }

        public Builder routingMetadata(Map<String, Object> routingMetadata) {
            this.routingMetadata = routingMetadata != null ? new HashMap<>(routingMetadata) : new HashMap<>();
            return this;
        }

        public Builder addRoutingMetadata(String key, Object value) {
            this.routingMetadata.put(key, value);
            return this;
        }

        public TriggerEvent build() {
            if (triggerType == null) {
                throw new IllegalArgumentException("triggerType is required");
            }
            if (triggerId == null || triggerId.isEmpty()) {
                throw new IllegalArgumentException("triggerId is required");
            }
            return new TriggerEvent(this);
        }
    }
}
