package com.harness.triggers;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for IntervalTrigger.
 */
class IntervalTriggerTest {

    private TriggerAction action;

    @BeforeEach
    void setUp() {
        action = new TriggerAction.Builder()
                .goal("Test goal")
                .build();
    }

    @Test
    void testIntervalTriggerCreation() {
        IntervalTrigger trigger = new IntervalTrigger(60, action);

        assertEquals(TriggerType.INTERVAL, trigger.getTriggerType());
        assertEquals(60, trigger.getIntervalSeconds());
        assertFalse(trigger.isStartImmediately());
        assertEquals(TriggerState.IDLE, trigger.getState());
    }

    @Test
    void testIntervalTriggerWithStartImmediately() {
        IntervalTrigger trigger = new IntervalTrigger(60, action, true);

        assertTrue(trigger.isStartImmediately());
    }

    @Test
    void testIntervalTriggerValidation() {
        // Interval too small
        assertThrows(IllegalArgumentException.class, () ->
                new IntervalTrigger(0, action));
    }

    @Test
    void testStartStop() throws InterruptedException {
        IntervalTrigger trigger = new IntervalTrigger(1, action);

        assertFalse(trigger.isRunning());

        trigger.start(event -> {}).join();
        assertTrue(trigger.isRunning());
        assertEquals(TriggerState.RUNNING, trigger.getState());

        // Wait a bit
        Thread.sleep(100);

        trigger.stop().join();
        assertFalse(trigger.isRunning());
        assertEquals(TriggerState.STOPPED, trigger.getState());
    }

    @Test
    void testFireImmediately() throws InterruptedException {
        AtomicInteger fireCount = new AtomicInteger(0);

        IntervalTrigger trigger = new IntervalTrigger(10, action, true);

        trigger.start(event -> fireCount.incrementAndGet()).join();

        // Should fire immediately
        Thread.sleep(200);
        assertTrue(fireCount.get() >= 1, "Should have fired at least once");

        trigger.stop().join();
    }

    @Test
    void testCreateEvent() {
        IntervalTrigger trigger = new IntervalTrigger(60, action);
        trigger.start(event -> {}).join();

        TriggerEvent event = trigger.createEvent(null);

        assertEquals(TriggerType.INTERVAL, event.getTriggerType());
        assertEquals(trigger.getId(), event.getTriggerId());
        assertEquals(60L, ((Number) event.getPayload().get("interval_seconds")).longValue());
    }

    @Test
    void testCustomTriggerId() {
        IntervalTrigger trigger = new IntervalTrigger(60, action);
        trigger.setId("custom-id");

        assertEquals("custom-id", trigger.getId());
    }

    @Test
    void testActionGetterSetter() {
        IntervalTrigger trigger = new IntervalTrigger(60, action);

        TriggerAction newAction = new TriggerAction.Builder()
                .goal("New goal")
                .build();

        trigger.setAction(newAction);
        assertEquals(newAction, trigger.getAction());
    }
}
