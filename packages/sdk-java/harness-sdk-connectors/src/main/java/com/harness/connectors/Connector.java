package com.harness.connectors;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;

/**
 * Connector abstract base class.
 *
 * <p>All external system integrations must inherit from this class.</p>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * public class MyConnector extends Connector {
 *     public MyConnector() {
 *         super(ConnectorType.CUSTOM);
 *     }
 *
 *     public CompletableFuture<Void> start(Consumer<ConnectorEvent> eventCallback) {
 *         this.eventCallback = eventCallback;
 *         this.state = ConnectorState.RUNNING;
 *         // Start listening for events...
 *         return CompletableFuture.completedFuture(null);
 *     }
 *
 *     public CompletableFuture<Void> stop() {
 *         this.state = ConnectorState.STOPPED;
 *         return CompletableFuture.completedFuture(null);
 *     }
 * }
 * }</pre>
 */
public abstract class Connector {
    protected final ConnectorType connectorType;
    protected String id;
    protected ConnectorState state = ConnectorState.IDLE;
    protected Consumer<ConnectorEvent> eventCallback;

    /**
     * Create a new Connector.
     *
     * @param connectorType The type of this connector
     */
    protected Connector(ConnectorType connectorType) {
        this.connectorType = connectorType;
        this.id = generateId();
    }

    /**
     * Start the connector.
     *
     * @param eventCallback Callback to send events to ConnectorManager
     * @return CompletableFuture that completes when started
     */
    public abstract CompletableFuture<Void> start(Consumer<ConnectorEvent> eventCallback);

    /**
     * Stop the connector.
     *
     * @return CompletableFuture that completes when stopped
     */
    public abstract CompletableFuture<Void> stop();

    /**
     * Create a standardized connector event.
     *
     * @param eventType Event type identifier
     * @param payload Event-specific data
     * @param source Source identifier
     * @return ConnectorEvent
     */
    public ConnectorEvent createEvent(String eventType, Map<String, Object> payload, String source) {
        return createEvent(eventType, payload, source, null);
    }

    /**
     * Create a standardized connector event with routing metadata.
     *
     * @param eventType Event type identifier
     * @param payload Event-specific data
     * @param source Source identifier
     * @param routingMetadata Metadata for routing responses back to source
     * @return ConnectorEvent
     */
    public ConnectorEvent createEvent(
            String eventType,
            Map<String, Object> payload,
            String source,
            Map<String, Object> routingMetadata) {

        return ConnectorEvent.builder()
                .connectorType(connectorType)
                .connectorId(id)
                .eventType(eventType)
                .source(source)
                .payload(payload != null ? payload : new HashMap<>())
                .routingMetadata(routingMetadata != null ? routingMetadata : new HashMap<>())
                .build();
    }

    /**
     * Check if connector is running.
     */
    public boolean isRunning() {
        return state == ConnectorState.RUNNING;
    }

    /**
     * Perform health check.
     */
    public CompletableFuture<Boolean> healthCheck() {
        return CompletableFuture.completedFuture(isRunning());
    }

    /**
     * Get the connector type.
     */
    public ConnectorType getConnectorType() {
        return connectorType;
    }

    /**
     * Get the connector ID.
     */
    public String getId() {
        return id;
    }

    /**
     * Set the connector ID.
     */
    public void setId(String id) {
        this.id = id;
    }

    /**
     * Get the connector state.
     */
    public ConnectorState getState() {
        return state;
    }

    /**
     * Generate a unique connector ID.
     */
    protected String generateId() {
        return connectorType.getValue() + "_" + UUID.randomUUID().toString().substring(0, 8);
    }

    @Override
    public String toString() {
        return getClass().getSimpleName() + "{id='" + id + "', state=" + state.getValue() + "}";
    }
}
