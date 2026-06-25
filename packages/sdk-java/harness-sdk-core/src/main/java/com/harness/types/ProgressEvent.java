package com.harness.types;

import java.time.Instant;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.Map;

/**
 * Progress event for tracking agent execution.
 *
 * @param type Event type
 * @param message Human-readable message
 * @param timestamp When the event occurred
 * @param data Additional event data (tool name, arguments, timing, etc.)
 * @param durationMs Duration in milliseconds (for timed events)
 */
public record ProgressEvent(
    ProgressEventType type,
    String message,
    Instant timestamp,
    Map<String, Object> data,
    Long durationMs
) {

    private static final DateTimeFormatter TIME_FORMATTER =
        DateTimeFormatter.ofPattern("HH:mm:ss").withZone(ZoneId.systemDefault());

    /**
     * Create a progress event with current timestamp.
     */
    public static ProgressEvent of(ProgressEventType type, String message) {
        return new ProgressEvent(type, message, Instant.now(), Map.of(), null);
    }

    /**
     * Create a progress event with data.
     */
    public static ProgressEvent of(ProgressEventType type, String message, Map<String, Object> data) {
        return new ProgressEvent(type, message, Instant.now(), data, null);
    }

    /**
     * Create a progress event with duration.
     */
    public static ProgressEvent of(ProgressEventType type, String message, Map<String, Object> data, long durationMs) {
        return new ProgressEvent(type, message, Instant.now(), data, durationMs);
    }

    /**
     * Create builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    @Override
    public String toString() {
        String ts = TIME_FORMATTER.format(timestamp);
        String duration = durationMs != null ? String.format(" (%dms)", durationMs) : "";
        return String.format("[%s] %s: %s%s", ts, type.name().toLowerCase(), message, duration);
    }

    public static class Builder {
        private ProgressEventType type;
        private String message;
        private Instant timestamp = Instant.now();
        private Map<String, Object> data = Map.of();
        private Long durationMs = null;

        public Builder type(ProgressEventType type) {
            this.type = type;
            return this;
        }

        public Builder message(String message) {
            this.message = message;
            return this;
        }

        public Builder timestamp(Instant timestamp) {
            this.timestamp = timestamp;
            return this;
        }

        public Builder data(Map<String, Object> data) {
            this.data = data;
            return this;
        }

        public Builder durationMs(long durationMs) {
            this.durationMs = durationMs;
            return this;
        }

        public ProgressEvent build() {
            return new ProgressEvent(type, message, timestamp, data, durationMs);
        }
    }
}
