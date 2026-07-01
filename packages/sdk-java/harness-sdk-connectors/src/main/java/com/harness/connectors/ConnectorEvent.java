package com.harness.connectors;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;

/**
 * Standardized external event.
 *
 * <p>All connectors must convert external events to this format.
 * The routingMetadata field enables "reply to original thread" functionality.</p>
 */
public class ConnectorEvent {
    private final ConnectorType connectorType;
    private final String connectorId;
    private final String eventType;
    private final String source;
    private final Instant timestamp;
    private final Map<String, Object> payload;
    private final String userId;
    private final String channelId;
    private final Map<String, Object> routingMetadata;

    private ConnectorEvent(Builder builder) {
        this.connectorType = builder.connectorType;
        this.connectorId = builder.connectorId;
        this.eventType = builder.eventType;
        this.source = builder.source;
        this.timestamp = builder.timestamp != null ? builder.timestamp : Instant.now();
        this.payload = new HashMap<>(builder.payload);
        this.userId = builder.userId;
        this.channelId = builder.channelId;
        this.routingMetadata = new HashMap<>(builder.routingMetadata);
    }

    /**
     * Check if this is a command event.
     */
    public boolean isCommand() {
        return eventType != null && eventType.endsWith(".command");
    }

    // Getters

    public ConnectorType getConnectorType() {
        return connectorType;
    }

    public String getConnectorId() {
        return connectorId;
    }

    public String getEventType() {
        return eventType;
    }

    public String getSource() {
        return source;
    }

    public Instant getTimestamp() {
        return timestamp;
    }

    public Map<String, Object> getPayload() {
        return new HashMap<>(payload);
    }

    public String getUserId() {
        return userId;
    }

    public String getChannelId() {
        return channelId;
    }

    public Map<String, Object> getRoutingMetadata() {
        return new HashMap<>(routingMetadata);
    }

    /**
     * Create a builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Builder for ConnectorEvent.
     */
    public static class Builder {
        private ConnectorType connectorType;
        private String connectorId;
        private String eventType;
        private String source;
        private Instant timestamp;
        private Map<String, Object> payload = new HashMap<>();
        private String userId;
        private String channelId;
        private Map<String, Object> routingMetadata = new HashMap<>();

        public Builder connectorType(ConnectorType connectorType) {
            this.connectorType = connectorType;
            return this;
        }

        public Builder connectorId(String connectorId) {
            this.connectorId = connectorId;
            return this;
        }

        public Builder eventType(String eventType) {
            this.eventType = eventType;
            return this;
        }

        public Builder source(String source) {
            this.source = source;
            return this;
        }

        public Builder timestamp(Instant timestamp) {
            this.timestamp = timestamp;
            return this;
        }

        public Builder payload(Map<String, Object> payload) {
            this.payload = new HashMap<>(payload);
            return this;
        }

        public Builder addPayload(String key, Object value) {
            this.payload.put(key, value);
            return this;
        }

        public Builder userId(String userId) {
            this.userId = userId;
            return this;
        }

        public Builder channelId(String channelId) {
            this.channelId = channelId;
            return this;
        }

        public Builder routingMetadata(Map<String, Object> routingMetadata) {
            this.routingMetadata = new HashMap<>(routingMetadata);
            return this;
        }

        public Builder addRoutingMetadata(String key, Object value) {
            this.routingMetadata.put(key, value);
            return this;
        }

        public ConnectorEvent build() {
            return new ConnectorEvent(this);
        }
    }

    @Override
    public String toString() {
        return "ConnectorEvent{" +
                "connectorType=" + connectorType +
                ", connectorId='" + connectorId + '\'' +
                ", eventType='" + eventType + '\'' +
                ", source='" + source + '\'' +
                '}';
    }
}
