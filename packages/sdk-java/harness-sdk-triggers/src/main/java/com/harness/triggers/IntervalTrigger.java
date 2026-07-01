package com.harness.triggers;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;

/**
 * Interval-based trigger for periodic execution.
 *
 * <p>Fires events at a fixed interval. Simpler than cron for
 * regular periodic tasks.</p>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * // Every 5 minutes
 * IntervalTrigger trigger = new IntervalTrigger(
 *     300,  // 5 minutes in seconds
 *     new TriggerAction.Builder()
 *         .goal("Health check")
 *         .build()
 * );
 *
 * // Every hour, fire immediately on start
 * IntervalTrigger trigger = new IntervalTrigger(
 *     3600,
 *     action,
 *     true  // startImmediately
 * );
 * }</pre>
 */
public class IntervalTrigger extends Trigger {
    private static final Logger logger = LoggerFactory.getLogger(IntervalTrigger.class);

    private final long intervalSeconds;
    private final boolean startImmediately;
    private final ScheduledExecutorService scheduler;

    private Consumer<TriggerEvent> callback;
    private java.util.concurrent.ScheduledFuture<?> scheduledFuture;
    private int fireCount = 0;

    /**
     * Create a new IntervalTrigger.
     *
     * @param intervalSeconds Time between firings (minimum 1 second)
     * @param action Action to execute when triggered
     */
    public IntervalTrigger(long intervalSeconds, TriggerAction action) {
        this(intervalSeconds, action, false);
    }

    /**
     * Create a new IntervalTrigger.
     *
     * @param intervalSeconds Time between firings (minimum 1 second)
     * @param action Action to execute when triggered
     * @param startImmediately Fire immediately when started
     */
    public IntervalTrigger(long intervalSeconds, TriggerAction action, boolean startImmediately) {
        super(TriggerType.INTERVAL);

        if (intervalSeconds < 1) {
            throw new IllegalArgumentException("intervalSeconds must be at least 1 second");
        }

        this.intervalSeconds = intervalSeconds;
        this.action = action;
        this.startImmediately = startImmediately;
        this.scheduler = Executors.newSingleThreadScheduledExecutor();
    }

    @Override
    public CompletableFuture<Void> start(Consumer<TriggerEvent> callback) {
        if (isRunning()) {
            logger.warn("IntervalTrigger {} is already running", id);
            return CompletableFuture.completedFuture(null);
        }

        this.callback = callback;
        setRunning();

        // Fire immediately if configured
        if (startImmediately) {
            fireEvent();
        }

        // Schedule periodic execution
        scheduledFuture = scheduler.scheduleAtFixedRate(
                this::fireEvent,
                startImmediately ? intervalSeconds : 0,
                intervalSeconds,
                TimeUnit.SECONDS
        );

        logger.info("IntervalTrigger {} started with interval {}s", id, intervalSeconds);
        return CompletableFuture.completedFuture(null);
    }

    @Override
    public CompletableFuture<Void> stop() {
        if (!isRunning()) {
            return CompletableFuture.completedFuture(null);
        }

        if (scheduledFuture != null) {
            scheduledFuture.cancel(false);
            scheduledFuture = null;
        }

        scheduler.shutdown();
        setStopped();
        logger.info("IntervalTrigger {} stopped after {} fires", id, fireCount);
        return CompletableFuture.completedFuture(null);
    }

    private void fireEvent() {
        if (!isRunning() || callback == null) {
            return;
        }

        try {
            fireCount++;
            TriggerEvent event = createEvent(
                    new HashMap<>(Map.of(
                            "interval_seconds", intervalSeconds,
                            "fire_count", fireCount
                    ))
            );

            logger.debug("IntervalTrigger {} firing event #{}", id, fireCount);
            callback.accept(event);

        } catch (Exception e) {
            logger.error("IntervalTrigger {} error: {}", id, e.getMessage());
            setError(e.getMessage());
        }
    }

    /**
     * Get the interval in seconds.
     */
    public long getIntervalSeconds() {
        return intervalSeconds;
    }

    /**
     * Get whether to start immediately.
     */
    public boolean isStartImmediately() {
        return startImmediately;
    }

    /**
     * Get the number of times this trigger has fired.
     */
    public int getFireCount() {
        return fireCount;
    }

    @Override
    public TriggerEvent createEvent(Map<String, Object> payload) {
        Map<String, Object> eventPayload = new HashMap<>();
        eventPayload.put("interval_seconds", intervalSeconds);
        eventPayload.put("fire_count", fireCount);
        if (payload != null) {
            eventPayload.putAll(payload);
        }
        return super.createEvent(eventPayload);
    }
}
