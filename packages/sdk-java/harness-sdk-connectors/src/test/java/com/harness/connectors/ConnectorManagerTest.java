package com.harness.connectors;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.Consumer;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for ConnectorManager.
 */
class ConnectorManagerTest {

    private ConnectorManager manager;

    @BeforeEach
    void setUp() {
        manager = new ConnectorManager();
    }

    @Test
    void testRegisterConnector() {
        TestConnector connector = new TestConnector();
        String id = manager.registerConnector(connector);

        assertNotNull(id);
        assertEquals(1, manager.getConnectorCount());
        assertEquals(connector, manager.getConnector(id));
    }

    @Test
    void testUnregisterConnector() {
        TestConnector connector = new TestConnector();
        String id = manager.registerConnector(connector);

        assertTrue(manager.unregisterConnector(id));
        assertEquals(0, manager.getConnectorCount());
        assertNull(manager.getConnector(id));
    }

    @Test
    void testRegisterOutputChannel() {
        OutputChannel channel = OutputChannel.builder()
                .type("console")
                .name("test-channel")
                .build();

        String name = manager.registerOutputChannel(channel);

        assertEquals("test-channel", name);
        assertEquals(channel, manager.getOutputChannel(name));
    }

    @Test
    void testStartStop() {
        TestConnector connector = new TestConnector();
        manager.registerConnector(connector);

        assertFalse(manager.isRunning());
        manager.start().join();
        assertTrue(manager.isRunning());
        assertTrue(connector.isRunning());

        manager.stop().join();
        assertFalse(manager.isRunning());
        assertFalse(connector.isRunning());
    }

    @Test
    void testEventHandler() {
        AtomicReference<ConnectorEvent> receivedEvent = new AtomicReference<>();
        manager.setEventHandler(receivedEvent::set);

        TestConnector connector = new TestConnector();
        manager.registerConnector(connector);
        manager.start().join();

        // Emit an event
        connector.emitEvent("test.event", Map.of("key", "value"));

        assertNotNull(receivedEvent.get());
        assertEquals("test.event", receivedEvent.get().getEventType());
        assertEquals("value", receivedEvent.get().getPayload().get("key"));
    }

    @Test
    void testRouteOutputConsole() {
        OutputChannel channel = OutputChannel.builder()
                .type("console")
                .name("console-out")
                .build();
        manager.registerOutputChannel(channel);

        List<OutputResult> results = manager.routeOutput(
                "Test result",
                List.of("console-out"),
                null
        ).join();

        assertEquals(1, results.size());
        assertTrue(results.get(0).isSuccess());
    }

    @Test
    void testRouteOutputUnknownChannel() {
        List<OutputResult> results = manager.routeOutput(
                "Test result",
                List.of("nonexistent"),
                null
        ).join();

        assertEquals(1, results.size());
        assertFalse(results.get(0).isSuccess());
        assertTrue(results.get(0).getError().contains("not found"));
    }

    @Test
    void testListConnectors() {
        TestConnector c1 = new TestConnector();
        TestConnector c2 = new TestConnector();
        manager.registerConnector(c1);
        manager.registerConnector(c2);

        List<Map<String, Object>> list = manager.listConnectors();

        assertEquals(2, list.size());
    }

    @Test
    void testListOutputChannels() {
        manager.registerOutputChannel(OutputChannel.builder()
                .type("console").name("ch1").build());
        manager.registerOutputChannel(OutputChannel.builder()
                .type("file").name("ch2").build());

        List<String> channels = manager.listOutputChannels();

        assertEquals(2, channels.size());
        assertTrue(channels.contains("ch1"));
        assertTrue(channels.contains("ch2"));
    }

    /**
     * Test connector implementation.
     */
    private static class TestConnector extends Connector {
        public TestConnector() {
            super(ConnectorType.CUSTOM);
        }

        @Override
        public CompletableFuture<Void> start(Consumer<ConnectorEvent> eventCallback) {
            this.eventCallback = eventCallback;
            this.state = ConnectorState.RUNNING;
            return CompletableFuture.completedFuture(null);
        }

        @Override
        public CompletableFuture<Void> stop() {
            this.state = ConnectorState.STOPPED;
            return CompletableFuture.completedFuture(null);
        }

        public void emitEvent(String eventType, Map<String, Object> payload) {
            if (eventCallback != null) {
                eventCallback.accept(createEvent(eventType, payload, "test"));
            }
        }
    }
}
