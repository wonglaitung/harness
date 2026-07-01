package com.harness.connectors;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;

/**
 * Slack connector for Slack App integration.
 *
 * <p>Features:</p>
 * <ul>
 *   <li>Receive Slack messages and commands</li>
 *   <li>Send messages to channels</li>
 *   <li>Thread reply support via routing_metadata</li>
 * </ul>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * SlackConnector slack = new SlackConnector(
 *     new SlackConfig.Builder()
 *         .botToken("xoxb-...")
 *         .appToken("xapp-...")  // For Socket Mode
 *         .build()
 * );
 *
 * slack.start(event -> {
 *     System.out.println("Received event: " + event.getEventType());
 * }).join();
 *
 * // Send message
 * slack.sendMessage("#general", "Hello!", null, "17123456.0001");
 * }</pre>
 */
public class SlackConnector extends Connector {
    private static final Logger logger = LoggerFactory.getLogger(SlackConnector.class);

    private final SlackConfig config;
    private SlackAPIClient apiClient;

    /**
     * Create a new SlackConnector.
     *
     * @param config Slack configuration
     */
    public SlackConnector(SlackConfig config) {
        super(ConnectorType.SLACK);
        this.config = config;
    }

    /**
     * Create a new SlackConnector with a specific ID.
     *
     * @param config Slack configuration
     * @param connectorId Connector ID
     */
    public SlackConnector(SlackConfig config, String connectorId) {
        super(ConnectorType.SLACK);
        this.config = config;
        this.id = connectorId;
    }

    @Override
    public CompletableFuture<Void> start(Consumer<ConnectorEvent> eventCallback) {
        this.eventCallback = eventCallback;

        try {
            // Initialize Slack API client
            this.apiClient = new SlackAPIClient(config.getBotToken(), config.getAppToken());
            this.state = ConnectorState.RUNNING;
            logger.info("SlackConnector started: {}", id);
            return CompletableFuture.completedFuture(null);
        } catch (Exception e) {
            logger.error("Failed to initialize Slack client: {}", e.getMessage());
            this.state = ConnectorState.ERROR;
            return CompletableFuture.failedFuture(e);
        }
    }

    /**
     * Handle a Slack event.
     *
     * <p>Parses the event and emits a ConnectorEvent if applicable.</p>
     *
     * @param event Raw Slack event
     */
    public void handleEvent(Map<String, Object> event) {
        ConnectorEvent connectorEvent = parseSlackEvent(event);
        if (connectorEvent != null && eventCallback != null) {
            eventCallback.accept(connectorEvent);
        }
    }

    /**
     * Parse Slack event into ConnectorEvent.
     *
     * <p>Extracts routing_metadata for thread replies.</p>
     */
    @SuppressWarnings("unchecked")
    private ConnectorEvent parseSlackEvent(Map<String, Object> event) {
        String eventType = (String) event.get("type");

        // Handle message events
        if ("message".equals(eventType)) {
            // Skip bot messages and channel join messages
            if (event.containsKey("bot_id") || "channel_join".equals(event.get("subtype"))) {
                return null;
            }

            // Extract routing metadata for thread replies
            Map<String, Object> routingMetadata = new HashMap<>();

            // Use thread_ts if available, otherwise use message ts
            if (event.containsKey("thread_ts")) {
                routingMetadata.put(RoutingKeys.SLACK_THREAD_TS, event.get("thread_ts"));
            } else if (event.containsKey("ts")) {
                routingMetadata.put(RoutingKeys.SLACK_THREAD_TS, event.get("ts"));
            }

            if (event.containsKey("channel")) {
                routingMetadata.put(RoutingKeys.SLACK_CHANNEL_ID, event.get("channel"));
            }

            Map<String, Object> payload = new HashMap<>();
            payload.put("text", event.get("text"));
            payload.put("user", event.get("user"));
            payload.put("channel", event.get("channel"));
            payload.put("ts", event.get("ts"));
            payload.put("thread_ts", event.get("thread_ts"));

            return createEvent(
                    "slack.message",
                    payload,
                    event.containsKey("user") ? (String) event.get("user") : "unknown",
                    routingMetadata
            );
        }

        // Handle slash commands
        if ("slash_command".equals(eventType)) {
            Map<String, Object> routingMetadata = new HashMap<>();
            routingMetadata.put(RoutingKeys.SLACK_CHANNEL_ID, event.get("channel_id"));

            Map<String, Object> payload = new HashMap<>();
            payload.put("command", event.get("command"));
            payload.put("text", event.get("text"));
            payload.put("user_id", event.get("user_id"));
            payload.put("channel_id", event.get("channel_id"));
            payload.put("trigger_id", event.get("trigger_id"));

            return createEvent(
                    "slack.command",
                    payload,
                    event.containsKey("user_id") ? (String) event.get("user_id") : "unknown",
                    routingMetadata
            );
        }

        // Handle app mentions
        if ("app_mention".equals(eventType)) {
            Map<String, Object> routingMetadata = new HashMap<>();

            if (event.containsKey("thread_ts")) {
                routingMetadata.put(RoutingKeys.SLACK_THREAD_TS, event.get("thread_ts"));
            } else if (event.containsKey("ts")) {
                routingMetadata.put(RoutingKeys.SLACK_THREAD_TS, event.get("ts"));
            }

            if (event.containsKey("channel")) {
                routingMetadata.put(RoutingKeys.SLACK_CHANNEL_ID, event.get("channel"));
            }

            Map<String, Object> payload = new HashMap<>();
            payload.put("text", event.get("text"));
            payload.put("user", event.get("user"));
            payload.put("channel", event.get("channel"));
            payload.put("ts", event.get("ts"));
            payload.put("thread_ts", event.get("thread_ts"));

            return createEvent(
                    "slack.mention",
                    payload,
                    event.containsKey("user") ? (String) event.get("user") : "unknown",
                    routingMetadata
            );
        }

        return null;
    }

    /**
     * Send a message to a Slack channel.
     *
     * @param channel Channel ID or name
     * @param text Message text
     * @param blocks Optional Slack Block Kit blocks
     * @param threadTs Thread timestamp to reply to a specific thread
     * @return CompletableFuture with success status
     */
    public CompletableFuture<Boolean> sendMessage(
            String channel,
            String text,
            List<Map<String, Object>> blocks,
            String threadTs) {

        if (apiClient == null) {
            logger.warn("Slack client not initialized");
            return CompletableFuture.completedFuture(false);
        }

        return apiClient.postMessage(channel, text, blocks, threadTs)
                .thenApply(success -> {
                    if (success) {
                        logger.debug("Sent Slack message to {}", channel);
                    }
                    return success;
                })
                .exceptionally(e -> {
                    logger.error("Failed to send Slack message: {}", e.getMessage());
                    return false;
                });
    }

    /**
     * Send a simple message to a Slack channel.
     *
     * @param channel Channel ID or name
     * @param text Message text
     * @return CompletableFuture with success status
     */
    public CompletableFuture<Boolean> sendMessage(String channel, String text) {
        return sendMessage(channel, text, null, null);
    }

    /**
     * Send an ephemeral message (visible only to a specific user).
     *
     * @param channel Channel ID
     * @param user User ID
     * @param text Message text
     * @param blocks Optional Slack Block Kit blocks
     * @return CompletableFuture with success status
     */
    public CompletableFuture<Boolean> sendEphemeral(
            String channel,
            String user,
            String text,
            List<Map<String, Object>> blocks) {

        if (apiClient == null) {
            return CompletableFuture.completedFuture(false);
        }

        return apiClient.postEphemeral(channel, user, text, blocks)
                .exceptionally(e -> {
                    logger.error("Failed to send ephemeral message: {}", e.getMessage());
                    return false;
                });
    }

    @Override
    public CompletableFuture<Void> stop() {
        this.apiClient = null;
        this.eventCallback = null;
        this.state = ConnectorState.STOPPED;
        logger.info("SlackConnector stopped: {}", id);
        return CompletableFuture.completedFuture(null);
    }

    /**
     * Internal Slack API client.
     *
     * <p>A lightweight client for Slack API calls.
     * In production, this would use a library like slack-api-client.</p>
     */
    private static class SlackAPIClient {
        private final String botToken;
        private final String appToken;

        SlackAPIClient(String botToken, String appToken) {
            this.botToken = botToken;
            this.appToken = appToken;
        }

        CompletableFuture<Boolean> postMessage(
                String channel,
                String text,
                List<Map<String, Object>> blocks,
                String threadTs) {

            // In production, use: POST /api/chat.postMessage
            logger.debug("Would send Slack message to {}: {}", channel, text);
            return CompletableFuture.completedFuture(true);
        }

        CompletableFuture<Boolean> postEphemeral(
                String channel,
                String user,
                String text,
                List<Map<String, Object>> blocks) {

            // In production, use: POST /api/chat.postEphemeral
            return CompletableFuture.completedFuture(true);
        }
    }
}
