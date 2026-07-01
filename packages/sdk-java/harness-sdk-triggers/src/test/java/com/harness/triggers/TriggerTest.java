package com.harness.triggers;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for Trigger types and base classes.
 */
class TriggerTest {

    @Test
    void testTriggerType() {
        assertEquals("cron", TriggerType.CRON.getValue());
        assertEquals("interval", TriggerType.INTERVAL.getValue());
        assertEquals("webhook", TriggerType.WEBHOOK.getValue());

        assertEquals(TriggerType.CRON, TriggerType.fromValue("cron"));
        assertEquals(TriggerType.EVENT, TriggerType.fromValue("unknown"));
    }

    @Test
    void testTriggerState() {
        assertEquals("idle", TriggerState.IDLE.getValue());
        assertEquals("running", TriggerState.RUNNING.getValue());
        assertEquals("stopped", TriggerState.STOPPED.getValue());
        assertEquals("error", TriggerState.ERROR.getValue());
    }

    @Test
    void testTriggerEventBuilder() {
        TriggerEvent event = new TriggerEvent.Builder()
                .triggerType(TriggerType.CRON)
                .triggerId("test-trigger")
                .addPayload("key", "value")
                .addRoutingMetadata("thread", "123")
                .build();

        assertEquals(TriggerType.CRON, event.getTriggerType());
        assertEquals("test-trigger", event.getTriggerId());
        assertEquals("value", event.getPayload().get("key"));
        assertEquals("123", event.getRoutingMetadata().get("thread"));
        assertTrue(event.isScheduled());
        assertFalse(event.isExternal());
    }

    @Test
    void testTriggerEventValidation() {
        // Missing triggerType
        assertThrows(IllegalArgumentException.class, () ->
                new TriggerEvent.Builder()
                        .triggerId("test")
                        .build());

        // Missing triggerId
        assertThrows(IllegalArgumentException.class, () ->
                new TriggerEvent.Builder()
                        .triggerType(TriggerType.CRON)
                        .build());
    }

    @Test
    void testTriggerActionBuilder() {
        TriggerAction action = new TriggerAction.Builder()
                .goal("Test goal")
                .workspaceDir("/workspace")
                .maxIterations(30)
                .timeoutSeconds(1800)
                .addSkill("skill1")
                .addOutputChannel("slack")
                .maxRetries(5)
                .retryDelaySeconds(10.0)
                .build();

        assertEquals("Test goal", action.getGoal());
        assertEquals("/workspace", action.getWorkspaceDir());
        assertEquals(30, action.getMaxIterations());
        assertEquals(1800, action.getTimeoutSeconds());
        assertEquals(1, action.getSkills().size());
        assertEquals("skill1", action.getSkills().get(0));
        assertEquals(1, action.getOutputChannels().size());
        assertEquals(5, action.getMaxRetries());
        assertEquals(10.0, action.getRetryDelaySeconds());
    }

    @Test
    void testTriggerActionValidation() {
        // Missing goal
        assertThrows(IllegalArgumentException.class, () ->
                new TriggerAction.Builder()
                        .maxIterations(10)
                        .build());

        // Invalid maxIterations
        assertThrows(IllegalArgumentException.class, () ->
                new TriggerAction.Builder()
                        .goal("test")
                        .maxIterations(0)
                        .build());

        // Invalid timeoutSeconds
        assertThrows(IllegalArgumentException.class, () ->
                new TriggerAction.Builder()
                        .goal("test")
                        .timeoutSeconds(0)
                        .build());
    }

    @Test
    void testTriggerActionToGoalConfig() {
        TriggerAction action = new TriggerAction.Builder()
                .goal("Test goal")
                .maxIterations(25)
                .build();

        TriggerEvent event = new TriggerEvent.Builder()
                .triggerType(TriggerType.INTERVAL)
                .triggerId("test")
                .addPayload("user", "john")
                .build();

        var config = action.toGoalConfig(event);
        assertTrue(config.getDescription().contains("Test goal"));
        assertTrue(config.getDescription().contains("user: john"));
        assertEquals(25, config.getMaxIterations());
    }
}
