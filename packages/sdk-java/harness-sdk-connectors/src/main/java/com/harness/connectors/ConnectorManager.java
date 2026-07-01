package com.harness.connectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Consumer;

/**
 * Connector manager for lifecycle and routing.
 *
 * <p>Responsibilities:</p>
 * <ul>
 *   <li>Manage connector lifecycle (start/stop)</li>
 *   <li>Route events from connectors</li>
 *   <li>Manage output channels</li>
 *   <li>Route Goal results to correct destinations</li>
 * </ul>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * ConnectorManager manager = new ConnectorManager();
 *
 * // Register connectors
 * WebhookConnector webhook = new WebhookConnector();
 * manager.registerConnector(webhook);
 *
 * // Register output channels
 * manager.registerOutputChannel(OutputChannel.builder()
 *     .type("slack")
 *     .name("alerts")
 *     .addConfig("channel", "#alerts")
 *     .build());
 *
 * // Start all
 * manager.start().join();
 * }</pre>
 */
public class ConnectorManager {
    private static final Logger logger = LoggerFactory.getLogger(ConnectorManager.class);

    private final Map<String, Connector> connectors = new ConcurrentHashMap<>();
    private final Map<String, OutputChannel> outputChannels = new ConcurrentHashMap<>();
    private final Map<String, OutputResult> lastResults = new ConcurrentHashMap<>();
    private volatile boolean running = false;
    private Consumer<ConnectorEvent> eventHandler;

    /**
     * Create a new ConnectorManager.
     */
    public ConnectorManager() {
    }

    /**
     * Set the event handler for connector events.
     *
     * @param handler Handler to receive connector events
     */
    public void setEventHandler(Consumer<ConnectorEvent> handler) {
        this.eventHandler = handler;
    }

    /**
     * Register a connector.
     *
     * @param connector Connector to register
     * @return Connector ID
     */
    public String registerConnector(Connector connector) {
        if (connector.getId() == null || connector.getId().isEmpty()) {
            connector.setId(connector.getConnectorType().getValue() + "_" +
                    Integer.toHexString(System.identityHashCode(connector)));
        }

        connectors.put(connector.getId(), connector);
        logger.info("Registered connector: {}", connector.getId());
        return connector.getId();
    }

    /**
     * Unregister a connector.
     *
     * @param connectorId Connector ID to unregister
     * @return True if connector was removed
     */
    public boolean unregisterConnector(String connectorId) {
        Connector removed = connectors.remove(connectorId);
        if (removed != null) {
            logger.info("Unregistered connector: {}", connectorId);
            return true;
        }
        return false;
    }

    /**
     * Register an output channel.
     *
     * @param channel OutputChannel configuration
     * @return Channel name
     */
    public String registerOutputChannel(OutputChannel channel) {
        outputChannels.put(channel.getName(), channel);
        logger.info("Registered output channel: {}", channel.getName());
        return channel.getName();
    }

    /**
     * Unregister an output channel.
     *
     * @param name Channel name
     * @return True if channel was removed
     */
    public boolean unregisterOutputChannel(String name) {
        return outputChannels.remove(name) != null;
    }

    /**
     * Start all connectors.
     */
    public CompletableFuture<Void> start() {
        running = true;

        List<CompletableFuture<Void>> futures = new ArrayList<>();

        for (Connector connector : connectors.values()) {
            futures.add(connector.start(this::onConnectorEvent)
                    .exceptionally(e -> {
                        logger.error("Failed to start connector {}: {}",
                                connector.getId(), e.getMessage());
                        return null;
                    }));
        }

        return CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]))
                .thenRun(() -> logger.info("Started {} connector(s)", connectors.size()));
    }

    /**
     * Stop all connectors.
     */
    public CompletableFuture<Void> stop() {
        running = false;

        List<CompletableFuture<Void>> futures = new ArrayList<>();

        for (Connector connector : connectors.values()) {
            futures.add(connector.stop()
                    .exceptionally(e -> {
                        logger.error("Error stopping connector {}: {}",
                                connector.getId(), e.getMessage());
                        return null;
                    }));
        }

        return CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]))
                .thenRun(() -> logger.info("Stopped all connectors"));
    }

    /**
     * Handle connector event.
     */
    private void onConnectorEvent(ConnectorEvent event) {
        logger.debug("Received event from {}: {}", event.getConnectorId(), event.getEventType());

        if (eventHandler != null) {
            try {
                eventHandler.accept(event);
            } catch (Exception e) {
                logger.error("Error handling connector event: {}", e.getMessage());
            }
        }
    }

    /**
     * Route result to specified channels.
     *
     * @param result Result to route
     * @param channels List of output channel names
     * @param routingMetadata Metadata for "reply to source"
     * @return List of OutputResult
     */
    public CompletableFuture<List<OutputResult>> routeOutput(
            Object result,
            List<String> channels,
            Map<String, Object> routingMetadata) {

        List<OutputResult> outputs = new ArrayList<>();
        List<CompletableFuture<Void>> futures = new ArrayList<>();

        for (String channelName : channels) {
            OutputChannel channel = outputChannels.get(channelName);
            if (channel == null) {
                logger.warn("Output channel not found: {}", channelName);
                outputs.add(OutputResult.builder()
                        .channelName(channelName)
                        .success(false)
                        .error("Channel not found")
                        .build());
                continue;
            }

            futures.add(sendToChannel(result, channel, routingMetadata)
                    .thenAccept(outputs::add));
        }

        return CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]))
                .thenApply(v -> outputs);
    }

    private CompletableFuture<OutputResult> sendToChannel(
            Object result,
            OutputChannel channel,
            Map<String, Object> routingMetadata) {

        return CompletableFuture.supplyAsync(() -> {
            try {
                String response = extractResponse(result);

                switch (channel.getType().toLowerCase()) {
                    case "console":
                        System.out.println("[" + channel.getName() + "] " + response);
                        return OutputResult.builder()
                                .channelName(channel.getName())
                                .success(true)
                                .message(response)
                                .build();

                    case "log":
                        logger.info("[{}] {}", channel.getName(), response);
                        return OutputResult.builder()
                                .channelName(channel.getName())
                                .success(true)
                                .message(response)
                                .build();

                    case "file":
                        return sendToFile(response, channel);

                    case "webhook":
                        return sendToWebhook(response, channel, routingMetadata);

                    case "slack":
                    case "github":
                        // These would require additional dependencies
                        logger.warn("Connector type '{}' requires additional implementation",
                                channel.getType());
                        return OutputResult.builder()
                                .channelName(channel.getName())
                                .success(false)
                                .error("Connector type not implemented: " + channel.getType())
                                .build();

                    default:
                        return OutputResult.builder()
                                .channelName(channel.getName())
                                .success(false)
                                .error("Unknown channel type: " + channel.getType())
                                .build();
                }

            } catch (Exception e) {
                logger.error("Failed to send to channel {}: {}", channel.getName(), e.getMessage());
                return OutputResult.builder()
                        .channelName(channel.getName())
                        .success(false)
                        .error(e.getMessage())
                        .build();
            }
        });
    }

    private OutputResult sendToFile(String response, OutputChannel channel) {
        try {
            String path = (String) channel.getConfig().getOrDefault("path", "output.txt");
            java.nio.file.Files.write(
                    java.nio.file.Paths.get(path),
                    ("\n---\n" + response + "\n").getBytes(),
                    java.nio.file.StandardOpenOption.CREATE,
                    java.nio.file.StandardOpenOption.APPEND);

            return OutputResult.builder()
                    .channelName(channel.getName())
                    .success(true)
                    .message("Written to " + path)
                    .build();

        } catch (Exception e) {
            return OutputResult.builder()
                    .channelName(channel.getName())
                    .success(false)
                    .error("File write error: " + e.getMessage())
                    .build();
        }
    }

    private OutputResult sendToWebhook(String response, OutputChannel channel,
            Map<String, Object> routingMetadata) {
        try {
            String url = (String) channel.getConfig().get("url");
            if (url == null) {
                return OutputResult.builder()
                        .channelName(channel.getName())
                        .success(false)
                        .error("Webhook URL not configured")
                        .build();
            }

            // Build JSON payload
            Map<String, Object> payload = new HashMap<>();
            payload.put("result", response);
            if (routingMetadata != null) {
                payload.put("routing", routingMetadata);
            }

            // Use Java's HttpClient (Java 11+)
            java.net.http.HttpClient client = java.net.http.HttpClient.newHttpClient();
            String json = new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(payload);

            java.net.http.HttpRequest request = java.net.http.HttpRequest.newBuilder()
                    .uri(java.net.URI.create(url))
                    .header("Content-Type", "application/json")
                    .POST(java.net.http.HttpRequest.BodyPublishers.ofString(json))
                    .build();

            java.net.http.HttpResponse<String> httpResponse = client.send(request,
                    java.net.http.HttpResponse.BodyHandlers.ofString());

            if (httpResponse.statusCode() >= 200 && httpResponse.statusCode() < 300) {
                return OutputResult.builder()
                        .channelName(channel.getName())
                        .success(true)
                        .message("Webhook sent successfully")
                        .build();
            } else {
                return OutputResult.builder()
                        .channelName(channel.getName())
                        .success(false)
                        .error("Webhook returned status " + httpResponse.statusCode())
                        .build();
            }

        } catch (Exception e) {
            return OutputResult.builder()
                    .channelName(channel.getName())
                    .success(false)
                    .error("Webhook error: " + e.getMessage())
                    .build();
        }
    }

    private String extractResponse(Object result) {
        if (result == null) {
            return "Task completed";
        }

        // Try to get finalResponse using reflection
        try {
            java.lang.reflect.Method method = result.getClass().getMethod("finalResponse");
            Object response = method.invoke(result);
            return response != null ? response.toString() : "Task completed";
        } catch (Exception e) {
            return result.toString();
        }
    }

    /**
     * List all connectors with their status.
     */
    public List<Map<String, Object>> listConnectors() {
        List<Map<String, Object>> list = new ArrayList<>();
        for (Connector connector : connectors.values()) {
            Map<String, Object> info = new HashMap<>();
            info.put("id", connector.getId());
            info.put("type", connector.getConnectorType().getValue());
            info.put("state", connector.getState().getValue());
            list.add(info);
        }
        return list;
    }

    /**
     * List all output channel names.
     */
    public List<String> listOutputChannels() {
        return new ArrayList<>(outputChannels.keySet());
    }

    /**
     * Get number of registered connectors.
     */
    public int getConnectorCount() {
        return connectors.size();
    }

    /**
     * Check if manager is running.
     */
    public boolean isRunning() {
        return running;
    }

    /**
     * Get a connector by ID.
     */
    public Connector getConnector(String connectorId) {
        return connectors.get(connectorId);
    }

    /**
     * Get an output channel by name.
     */
    public OutputChannel getOutputChannel(String name) {
        return outputChannels.get(name);
    }
}
