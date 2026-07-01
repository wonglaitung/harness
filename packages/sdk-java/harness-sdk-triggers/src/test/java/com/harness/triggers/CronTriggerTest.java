package com.harness.triggers;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for CronTrigger.
 */
class CronTriggerTest {

    private TriggerAction action;

    @BeforeEach
    void setUp() {
        action = new TriggerAction.Builder()
                .goal("Test goal")
                .build();
    }

    @Test
    void testCronTriggerCreation() {
        CronTrigger trigger = new CronTrigger("0 9 * * *", action);

        assertEquals(TriggerType.CRON, trigger.getTriggerType());
        assertEquals("0 9 * * *", trigger.getSchedule());
        assertEquals("local", trigger.getTimezone());
        assertEquals(TriggerState.IDLE, trigger.getState());
    }

    @Test
    void testCronTriggerWithTimezone() {
        CronTrigger trigger = new CronTrigger("0 9 * * *", action, "UTC", 0);

        assertEquals("UTC", trigger.getTimezone());
        assertEquals(0, trigger.getJitterSeconds());
    }

    @Test
    void testCronTriggerValidation() {
        // Invalid cron expression (too few fields)
        assertThrows(IllegalArgumentException.class, () ->
                new CronTrigger("0 9 *", action));
    }

    @Test
    void testStartStop() throws InterruptedException {
        CronTrigger trigger = new CronTrigger("* * * * *", action);  // Every minute

        assertFalse(trigger.isRunning());

        trigger.start(event -> {}).join();
        assertTrue(trigger.isRunning());
        assertEquals(TriggerState.RUNNING, trigger.getState());

        trigger.stop().join();
        assertFalse(trigger.isRunning());
        assertEquals(TriggerState.STOPPED, trigger.getState());
    }

    @Test
    void testCreateEvent() {
        CronTrigger trigger = new CronTrigger("0 9 * * *", action);
        trigger.start(event -> {}).join();

        TriggerEvent event = trigger.createEvent(null);

        assertEquals(TriggerType.CRON, event.getTriggerType());
        assertEquals(trigger.getId(), event.getTriggerId());
        assertEquals("0 9 * * *", event.getPayload().get("schedule"));
    }

    @Test
    void testCustomTriggerId() {
        CronTrigger trigger = new CronTrigger("0 9 * * *", action);
        trigger.setId("custom-cron-id");

        assertEquals("custom-cron-id", trigger.getId());
    }
}
