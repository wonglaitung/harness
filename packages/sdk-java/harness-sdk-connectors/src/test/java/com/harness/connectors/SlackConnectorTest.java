package com.harness.connectors;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for SlackConnector.
 */
class SlackConnectorTest {

    private SlackConfig config;

    @BeforeEach
    void setUp() {
        config = new SlackConfig.Builder()
                .botToken("xoxb-test-token")
                .appToken("xapp-test-token")
                .signingSecret("test-secret")
                .commandPrefix("/harness")
                .allowedChannels(Arrays.asList("C12345", "C67890"))
                .build();
    }

    @Test
    void testConfigBuilder() {
        assertEquals("xoxb-test-token", config.getBotToken());
        assertEquals("xapp-test-token", config.getAppToken());
        assertEquals("test-secret", config.getSigningSecret());
        assertEquals("/harness", config.getCommandPrefix());
        assertEquals(2, config.getAllowedChannels().size());
    }

    @Test
    void testConfigValidation() {
        // Missing botToken
        assertThrows(IllegalArgumentException.class, () ->
                new SlackConfig.Builder()
                        .appToken("xapp-test")
                        .build());
    }

    @Test
    void testDefaultCommandPrefix() {
        SlackConfig simpleConfig = new SlackConfig.Builder()
                .botToken("xoxb-test")
                .build();

        assertEquals("/harness", simpleConfig.getCommandPrefix());
    }

    @Test
    void testStartStop() {
        SlackConnector connector = new SlackConnector(config);

        assertFalse(connector.isRunning());

        connector.start(event -> {}).join();
        assertTrue(connector.isRunning());

        connector.stop().join();
        assertFalse(connector.isRunning());
    }

    @Test
    void testHandleMessageEvent() {
        SlackConnector connector = new SlackConnector(config);
        AtomicReference<ConnectorEvent> capturedEvent = new AtomicReference<>();

        connector.start(capturedEvent::set).join();

        Map<String, Object> event = new HashMap<>();
        event.put("type", "message");
        event.put("text", "Hello, bot!");
        event.put("user", "U12345");
        event.put("channel", "C12345");
        event.put("ts", "17123456.0001");

        connector.handleEvent(event);

        assertNotNull(capturedEvent.get());
        assertEquals("slack.message", capturedEvent.get().getEventType());
        assertEquals("U12345", capturedEvent.get().getSource());
        assertEquals("C12345", capturedEvent.get().getRoutingMetadata().get(RoutingKeys.SLACK_CHANNEL_ID));
        assertEquals("17123456.0001", capturedEvent.get().getRoutingMetadata().get(RoutingKeys.SLACK_THREAD_TS));
    }

    @Test
    void testHandleMessageWithThread() {
        SlackConnector connector = new SlackConnector(config);
        AtomicReference<ConnectorEvent> capturedEvent = new AtomicReference<>();

        connector.start(capturedEvent::set).join();

        Map<String, Object> event = new HashMap<>();
        event.put("type", "message");
        event.put("text", "Reply to thread");
        event.put("user", "U12345");
        event.put("channel", "C12345");
        event.put("ts", "17123457.0001");
        event.put("thread_ts", "17123456.0001");

        connector.handleEvent(event);

        assertNotNull(capturedEvent.get());
        assertEquals("17123456.0001", capturedEvent.get().getRoutingMetadata().get(RoutingKeys.SLACK_THREAD_TS));
    }

    @Test
    void testHandleBotMessageSkipped() {
        SlackConnector connector = new SlackConnector(config);
        AtomicReference<ConnectorEvent> capturedEvent = new AtomicReference<>();

        connector.start(capturedEvent::set).join();

        Map<String, Object> event = new HashMap<>();
        event.put("type", "message");
        event.put("text", "Bot message");
        event.put("bot_id", "B12345");  // Bot message

        connector.handleEvent(event);

        assertNull(capturedEvent.get());
    }

    @Test
    void testHandleSlashCommand() {
        SlackConnector connector = new SlackConnector(config);
        AtomicReference<ConnectorEvent> capturedEvent = new AtomicReference<>();

        connector.start(capturedEvent::set).join();

        Map<String, Object> event = new HashMap<>();
        event.put("type", "slash_command");
        event.put("command", "/harness");
        event.put("text", "run tests");
        event.put("user_id", "U12345");
        event.put("channel_id", "C12345");
        event.put("trigger_id", "T12345");

        connector.handleEvent(event);

        assertNotNull(capturedEvent.get());
        assertEquals("slack.command", capturedEvent.get().getEventType());
        assertTrue(capturedEvent.get().isCommand());
        assertEquals("C12345", capturedEvent.get().getRoutingMetadata().get(RoutingKeys.SLACK_CHANNEL_ID));
    }

    @Test
    void testHandleAppMention() {
        SlackConnector connector = new SlackConnector(config);
        AtomicReference<ConnectorEvent> capturedEvent = new AtomicReference<>();

        connector.start(capturedEvent::set).join();

        Map<String, Object> event = new HashMap<>();
        event.put("type", "app_mention");
        event.put("text", "<@BOT_ID> help");
        event.put("user", "U12345");
        event.put("channel", "C12345");
        event.put("ts", "17123458.0001");

        connector.handleEvent(event);

        assertNotNull(capturedEvent.get());
        assertEquals("slack.mention", capturedEvent.get().getEventType());
        assertEquals("C12345", capturedEvent.get().getRoutingMetadata().get(RoutingKeys.SLACK_CHANNEL_ID));
    }

    @Test
    void testSendMessage() {
        SlackConnector connector = new SlackConnector(config);
        connector.start(event -> {}).join();

        Boolean result = connector.sendMessage("C12345", "Hello!").join();
        assertTrue(result);
    }

    @Test
    void testSendMessageWithThread() {
        SlackConnector connector = new SlackConnector(config);
        connector.start(event -> {}).join();

        Boolean result = connector.sendMessage("C12345", "Reply!", null, "17123456.0001").join();
        assertTrue(result);
    }

    @Test
    void testSendEphemeral() {
        SlackConnector connector = new SlackConnector(config);
        connector.start(event -> {}).join();

        Boolean result = connector.sendEphemeral("C12345", "U12345", "Private message", null).join();
        assertTrue(result);
    }

    @Test
    void testConnectorType() {
        SlackConnector connector = new SlackConnector(config);
        assertEquals(ConnectorType.SLACK, connector.getConnectorType());
    }

    @Test
    void testCustomConnectorId() {
        SlackConnector connector = new SlackConnector(config, "custom-slack-id");
        assertEquals("custom-slack-id", connector.getId());
    }
}
