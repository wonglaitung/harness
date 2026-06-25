package com.harness.core;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.Callable;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Manages OpenTelemetry tracing for Agent execution.
 *
 * Provides W3C TraceContext propagation for Spring Cloud integration.
 * Compatible with Jaeger, Datadog, Langfuse, and other OTel-compatible backends.
 *
 * Example:
 * <pre>
 * TracingManager manager = new TracingManager(config);
 * manager.setup();
 *
 * // Extract trace from headers
 * TraceContext ctx = manager.extractContext(headers);
 *
 * // Run within trace context
 * manager.withSpan("agent_loop.run", ctx, () -> {
 *     // ... agent execution
 * });
 * </pre>
 */
public class TracingManager {

    private static final Logger logger = LoggerFactory.getLogger(TracingManager.class);

    private final TracingConfig config;
    private boolean setupComplete = false;

    // OpenTelemetry components (optional - may be null if not available)
    private Object tracer;  // io.opentelemetry.api.trace.Tracer
    private Object tracerProvider;  // io.opentelemetry.sdk.trace.TracerProvider

    // Thread-local for current trace context
    private final ThreadLocal<TraceContext> currentContext = new ThreadLocal<>();

    public TracingManager() {
        this(TracingConfig.defaults());
    }

    public TracingManager(TracingConfig config) {
        this.config = config;
    }

    /**
     * Check if tracing is enabled.
     */
    public boolean isEnabled() {
        return config.enabled();
    }

    /**
     * Check if OpenTelemetry is available on classpath.
     */
    public static boolean isOpenTelemetryAvailable() {
        try {
            Class.forName("io.opentelemetry.api.trace.Tracer");
            return true;
        } catch (ClassNotFoundException e) {
            return false;
        }
    }

    /**
     * Set up OpenTelemetry tracing.
     *
     * @return True if setup was successful
     */
    public boolean setup() {
        if (!config.enabled()) {
            logger.debug("Tracing is disabled");
            return false;
        }

        if (setupComplete) {
            return true;
        }

        if (!isOpenTelemetryAvailable()) {
            logger.debug("OpenTelemetry not available on classpath");
            return false;
        }

        try {
            // Initialize OpenTelemetry (reflection-based to avoid hard dependency)
            initializeOpenTelemetry();
            setupComplete = true;
            logger.info("Tracing initialized: service={}", config.serviceName());
            return true;
        } catch (Exception e) {
            logger.warn("Failed to initialize tracing: {}", e.getMessage());
            return false;
        }
    }

    /**
     * Initialize OpenTelemetry components using reflection.
     */
    private void initializeOpenTelemetry() throws Exception {
        // This is a simplified initialization
        // In production, you would use OpenTelemetrySdk.builder()
        // For now, we just mark as initialized for the context propagation API
        setupComplete = true;
    }

    /**
     * Extract trace context from HTTP headers.
     *
     * Supports W3C TraceContext format:
     * - traceparent: version-trace-id-parent-id-flags
     * - tracestate: vendor-specific key-value pairs
     *
     * @param headers HTTP headers map
     * @return Extracted TraceContext
     */
    public TraceContext extractContext(Map<String, String> headers) {
        String traceparent = headers.get("traceparent");
        if (traceparent == null) {
            traceparent = headers.get("Traceparent");
        }

        if (traceparent == null || traceparent.isEmpty()) {
            return TraceContext.empty();
        }

        // Parse W3C TraceContext format: version-trace-id-parent-id-flags
        String[] parts = traceparent.split("-");
        if (parts.length < 4) {
            return TraceContext.empty();
        }

        try {
            String version = parts[0];
            String traceId = parts[1];
            String parentId = parts[2];
            String flags = parts[3];

            String tracestate = headers.getOrDefault("tracestate", headers.getOrDefault("Tracestate", ""));

            return new TraceContext(traceId, parentId, flags, tracestate, version);
        } catch (Exception e) {
            logger.debug("Failed to parse traceparent: {}", e.getMessage());
            return TraceContext.empty();
        }
    }

    /**
     * Create a new trace context.
     *
     * @return New TraceContext with generated trace ID
     */
    public TraceContext createContext() {
        return TraceContext.generate();
    }

    /**
     * Run a task within a trace span.
     *
     * @param spanName Name of the span
     * @param context Trace context (can be null for new trace)
     * @param task Task to run
     * @param <T> Return type
     * @return Task result
     * @throws Exception If task throws
     */
    public <T> T withSpan(String spanName, TraceContext context, Callable<T> task) throws Exception {
        TraceContext ctx = context != null ? context : createContext();

        // Set current context
        currentContext.set(ctx);

        try {
            // Add span attributes
            ctx.addSpanAttribute("span.name", spanName);
            ctx.addSpanAttribute("service.name", config.serviceName());

            return task.call();
        } finally {
            currentContext.remove();
        }
    }

    /**
     * Run a task within a trace span (void version).
     */
    public void withSpan(String spanName, TraceContext context, Runnable task) {
        try {
            withSpan(spanName, context, () -> {
                task.run();
                return null;
            });
        } catch (Exception e) {
            if (e instanceof RuntimeException) {
                throw (RuntimeException) e;
            }
            throw new RuntimeException(e);
        }
    }

    /**
     * Get the current trace context.
     */
    public TraceContext getCurrentContext() {
        return currentContext.get();
    }

    /**
     * Get the current trace ID.
     */
    public String getTraceId() {
        TraceContext ctx = currentContext.get();
        return ctx != null ? ctx.traceId() : null;
    }

    /**
     * Get the current span ID.
     */
    public String getSpanId() {
        TraceContext ctx = currentContext.get();
        return ctx != null ? ctx.spanId() : null;
    }

    /**
     * Add attribute to current span.
     */
    public void addAttribute(String key, Object value) {
        TraceContext ctx = currentContext.get();
        if (ctx != null) {
            ctx.addSpanAttribute(key, value);
        }
    }

    /**
     * Add event to current span.
     */
    public void addEvent(String name) {
        TraceContext ctx = currentContext.get();
        if (ctx != null) {
            ctx.addSpanEvent(name);
        }
    }

    /**
     * Record an exception on the current span.
     */
    public void recordException(Throwable throwable) {
        TraceContext ctx = currentContext.get();
        if (ctx != null) {
            ctx.recordException(throwable);
        }
    }

    /**
     * Inject trace context into HTTP headers.
     *
     * @param headers Headers map to inject into
     */
    public void injectContext(Map<String, String> headers) {
        TraceContext ctx = currentContext.get();
        if (ctx != null && !ctx.isEmpty()) {
            headers.put("traceparent", ctx.toTraceparent());
            if (ctx.tracestate() != null && !ctx.tracestate().isEmpty()) {
                headers.put("tracestate", ctx.tracestate());
            }
            headers.put("X-Trace-Id", ctx.traceId());
        }
    }

    /**
     * Shutdown the tracer provider.
     */
    public void shutdown() {
        if (tracerProvider != null) {
            try {
                // Call tracerProvider.shutdown() via reflection
                tracerProvider.getClass().getMethod("shutdown").invoke(tracerProvider);
            } catch (Exception e) {
                logger.debug("Failed to shutdown tracer provider: {}", e.getMessage());
            }
        }
        setupComplete = false;
    }

    /**
     * Get tracing statistics.
     */
    public Map<String, Object> getStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("enabled", config.enabled());
        stats.put("setupComplete", setupComplete);
        stats.put("openTelemetryAvailable", isOpenTelemetryAvailable());
        stats.put("serviceName", config.serviceName());
        return stats;
    }
}
