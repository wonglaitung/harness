package com.harness.core;

import java.security.SecureRandom;
import java.util.HashMap;
import java.util.Map;

/**
 * Represents a W3C TraceContext for distributed tracing.
 *
 * W3C TraceContext format:
 * - traceparent: version-trace-id-parent-id-flags
 *   - version: 2 hex chars (usually "00")
 *   - trace-id: 32 hex chars (16 bytes)
 *   - parent-id: 16 hex chars (8 bytes)
 *   - flags: 2 hex chars (sampled = "01")
 * - tracestate: vendor-specific key-value pairs
 *
 * Example:
 * <pre>
 * // Create new context
 * TraceContext ctx = TraceContext.generate();
 *
 * // Parse from header
 * TraceContext ctx = TraceContext.fromTraceparent("00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01");
 *
 * // Convert to header
 * String header = ctx.toTraceparent();
 * </pre>
 */
public class TraceContext {

    private static final SecureRandom RANDOM = new SecureRandom();

    private final String traceId;       // 32 hex chars
    private final String spanId;        // 16 hex chars (also called parent-id)
    private final String flags;         // 2 hex chars
    private final String tracestate;    // Optional vendor-specific data
    private final String version;       // 2 hex chars (usually "00")

    // Span attributes and events (for current span)
    private final Map<String, Object> attributes = new HashMap<>();
    private final java.util.List<SpanEvent> events = new java.util.ArrayList<>();

    /**
     * Empty context (no trace).
     */
    public static final TraceContext EMPTY = new TraceContext("", "", "", "", "");

    public TraceContext(String traceId, String spanId, String flags, String tracestate, String version) {
        this.traceId = traceId != null ? traceId : "";
        this.spanId = spanId != null ? spanId : "";
        this.flags = flags != null ? flags : "01";
        this.tracestate = tracestate != null ? tracestate : "";
        this.version = version != null ? version : "00";
    }

    /**
     * Create an empty context.
     */
    public static TraceContext empty() {
        return EMPTY;
    }

    /**
     * Generate a new trace context.
     */
    public static TraceContext generate() {
        return new TraceContext(
            generateTraceId(),
            generateSpanId(),
            "01",  // sampled
            "",
            "00"
        );
    }

    /**
     * Parse from traceparent header.
     *
     * @param traceparent Header value (e.g., "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01")
     * @return Parsed TraceContext or EMPTY if invalid
     */
    public static TraceContext fromTraceparent(String traceparent) {
        if (traceparent == null || traceparent.isEmpty()) {
            return EMPTY;
        }

        String[] parts = traceparent.split("-");
        if (parts.length < 4) {
            return EMPTY;
        }

        return new TraceContext(parts[1], parts[2], parts[3], "", parts[0]);
    }

    /**
     * Check if this context is empty (no trace).
     */
    public boolean isEmpty() {
        return traceId == null || traceId.isEmpty();
    }

    /**
     * Check if sampling is enabled.
     */
    public boolean isSampled() {
        return "01".equals(flags);
    }

    /**
     * Convert to traceparent header format.
     */
    public String toTraceparent() {
        if (isEmpty()) {
            return "";
        }
        return String.format("%s-%s-%s-%s", version, traceId, spanId, flags);
    }

    /**
     * Create a child context (same trace, new span).
     */
    public TraceContext createChild() {
        return new TraceContext(
            this.traceId,
            generateSpanId(),
            this.flags,
            this.tracestate,
            this.version
        );
    }

    // -------------------------------------------------------------------------
    // Span operations
    // -------------------------------------------------------------------------

    /**
     * Add an attribute to the current span.
     */
    public void addSpanAttribute(String key, Object value) {
        if (!isEmpty()) {
            attributes.put(key, value);
        }
    }

    /**
     * Add an event to the current span.
     */
    public void addSpanEvent(String name) {
        if (!isEmpty()) {
            events.add(new SpanEvent(name, System.currentTimeMillis()));
        }
    }

    /**
     * Add an event with attributes.
     */
    public void addSpanEvent(String name, Map<String, Object> eventAttributes) {
        if (!isEmpty()) {
            events.add(new SpanEvent(name, System.currentTimeMillis(), eventAttributes));
        }
    }

    /**
     * Record an exception on this span.
     */
    public void recordException(Throwable throwable) {
        if (!isEmpty() && throwable != null) {
            addSpanAttribute("exception.type", throwable.getClass().getName());
            addSpanAttribute("exception.message", throwable.getMessage());
            addSpanEvent("exception");
        }
    }

    /**
     * Get span attributes.
     */
    public Map<String, Object> getAttributes() {
        return new HashMap<>(attributes);
    }

    /**
     * Get span events.
     */
    public java.util.List<SpanEvent> getEvents() {
        return new java.util.ArrayList<>(events);
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    public String traceId() { return traceId; }
    public String spanId() { return spanId; }
    public String flags() { return flags; }
    public String tracestate() { return tracestate; }
    public String version() { return version; }

    // -------------------------------------------------------------------------
    // ID generation
    // -------------------------------------------------------------------------

    /**
     * Generate a random trace ID (32 hex chars).
     */
    public static String generateTraceId() {
        byte[] bytes = new byte[16];
        RANDOM.nextBytes(bytes);
        return bytesToHex(bytes);
    }

    /**
     * Generate a random span ID (16 hex chars).
     */
    public static String generateSpanId() {
        byte[] bytes = new byte[8];
        RANDOM.nextBytes(bytes);
        return bytesToHex(bytes);
    }

    private static String bytesToHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }

    // -------------------------------------------------------------------------
    // Inner class for span events
    // -------------------------------------------------------------------------

    /**
     * Represents a span event.
     */
    public static class SpanEvent {
        private final String name;
        private final long timestamp;
        private final Map<String, Object> attributes;

        public SpanEvent(String name, long timestamp) {
            this(name, timestamp, Map.of());
        }

        public SpanEvent(String name, long timestamp, Map<String, Object> attributes) {
            this.name = name;
            this.timestamp = timestamp;
            this.attributes = attributes != null ? attributes : Map.of();
        }

        public String name() { return name; }
        public long timestamp() { return timestamp; }
        public Map<String, Object> attributes() { return attributes; }
    }
}
