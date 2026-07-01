package com.harness.triggers;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.temporal.ChronoUnit;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;

/**
 * Cron-based trigger for scheduled execution.
 *
 * <p>Uses cron expressions to determine when to fire events.
 * Supports standard 5-field cron format: minute hour day month weekday</p>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * // Daily at 9:00 AM
 * CronTrigger trigger = new CronTrigger(
 *     "0 9 * * *",
 *     new TriggerAction.Builder()
 *         .goal("Generate daily report")
 *         .build()
 * );
 *
 * // Every hour with 5-minute jitter
 * CronTrigger trigger = new CronTrigger(
 *     "0 * * * *",
 *     action,
 *     300  // 5-minute jitter
 * );
 * }</pre>
 */
public class CronTrigger extends Trigger {
    private static final Logger logger = LoggerFactory.getLogger(CronTrigger.class);

    private final String schedule;
    private final String timezone;
    private final int jitterSeconds;
    private final ScheduledExecutorService scheduler;

    private Consumer<TriggerEvent> callback;
    private java.util.concurrent.ScheduledFuture<?> scheduledFuture;
    private int fireCount = 0;

    /**
     * Create a new CronTrigger.
     *
     * @param schedule Cron expression (5 fields: minute hour day month weekday)
     * @param action Action to execute when triggered
     */
    public CronTrigger(String schedule, TriggerAction action) {
        this(schedule, action, "local", 0);
    }

    /**
     * Create a new CronTrigger.
     *
     * @param schedule Cron expression
     * @param action Action to execute
     * @param timezone Timezone for schedule ("local", "UTC", or timezone name)
     * @param jitterSeconds Maximum random delay in seconds (0 = no jitter)
     */
    public CronTrigger(String schedule, TriggerAction action, String timezone, int jitterSeconds) {
        super(TriggerType.CRON);
        this.schedule = schedule;
        this.action = action;
        this.timezone = timezone;
        this.jitterSeconds = jitterSeconds;
        this.scheduler = Executors.newSingleThreadScheduledExecutor();

        // Validate cron expression (simplified)
        validateCronExpression(schedule);
    }

    private void validateCronExpression(String schedule) {
        String[] parts = schedule.split("\\s+");
        if (parts.length != 5) {
            throw new IllegalArgumentException(
                    "Invalid cron expression '" + schedule + "'. Expected 5 fields: minute hour day month weekday");
        }
    }

    @Override
    public CompletableFuture<Void> start(Consumer<TriggerEvent> callback) {
        if (isRunning()) {
            logger.warn("CronTrigger {} is already running", id);
            return CompletableFuture.completedFuture(null);
        }

        this.callback = callback;
        setRunning();

        // Calculate initial delay to next scheduled time
        long initialDelay = calculateDelayToNextRun();

        // Schedule with fixed rate (simplified: check every minute)
        scheduledFuture = scheduler.scheduleAtFixedRate(
                this::fireEvent,
                initialDelay,
                60, // Check every minute
                TimeUnit.SECONDS
        );

        logger.info("CronTrigger {} started with schedule '{}', next run in {}s", id, schedule, initialDelay);
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
        logger.info("CronTrigger {} stopped after {} fires", id, fireCount);
        return CompletableFuture.completedFuture(null);
    }

    private void fireEvent() {
        if (!isRunning() || callback == null) {
            return;
        }

        try {
            // Check if current time matches cron schedule
            if (!matchesSchedule()) {
                return;
            }

            fireCount++;
            TriggerEvent event = createEvent(
                    new HashMap<>(Map.of(
                            "schedule", schedule,
                            "timezone", timezone,
                            "fire_count", fireCount
                    ))
            );

            logger.debug("CronTrigger {} firing event #{}", id, fireCount);
            callback.accept(event);

        } catch (Exception e) {
            logger.error("CronTrigger {} error: {}", id, e.getMessage());
            setError(e.getMessage());
        }
    }

    private boolean matchesSchedule() {
        // Simplified cron matching - in production, use a cron library
        LocalDateTime now = LocalDateTime.now();
        String[] parts = schedule.split("\\s+");

        int minute = parseCronField(parts[0], now.getMinute(), 0, 59);
        int hour = parseCronField(parts[1], now.getHour(), 0, 23);
        int dayOfMonth = parseCronField(parts[2], now.getDayOfMonth(), 1, 31);
        int month = parseCronField(parts[3], now.getMonthValue(), 1, 12);
        int dayOfWeek = parseCronField(parts[4], now.getDayOfWeek().getValue() % 7, 0, 6);

        return minute == now.getMinute() &&
               hour == now.getHour() &&
               (dayOfMonth == now.getDayOfMonth() || dayOfMonth == -1) &&
               (month == now.getMonthValue() || month == -1);
    }

    private int parseCronField(String field, int currentValue, int min, int max) {
        if ("*".equals(field)) {
            return currentValue; // Match any
        }
        try {
            return Integer.parseInt(field);
        } catch (NumberFormatException e) {
            return currentValue; // Default to current for complex expressions
        }
    }

    private long calculateDelayToNextRun() {
        // Simplified: return delay to next minute boundary
        LocalDateTime now = LocalDateTime.now();
        LocalDateTime nextMinute = now.truncatedTo(ChronoUnit.MINUTES).plusMinutes(1);
        return ChronoUnit.SECONDS.between(now, nextMinute);
    }

    /**
     * Get the cron schedule.
     */
    public String getSchedule() {
        return schedule;
    }

    /**
     * Get the timezone.
     */
    public String getTimezone() {
        return timezone;
    }

    /**
     * Get the jitter seconds.
     */
    public int getJitterSeconds() {
        return jitterSeconds;
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
        eventPayload.put("schedule", schedule);
        eventPayload.put("timezone", timezone);
        eventPayload.put("fire_count", fireCount);
        if (payload != null) {
            eventPayload.putAll(payload);
        }
        return super.createEvent(eventPayload);
    }
}
