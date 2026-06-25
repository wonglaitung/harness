package com.harness.core;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Consumer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.types.ProgressEvent;
import com.harness.types.TokenUsage;

/**
 * Collects and exports metrics for Agent execution.
 *
 * This collector integrates with AgentHarness to track:
 * - Loop iterations
 * - Tool calls (success/failure)
 * - Token usage
 * - Execution duration
 *
 * Supports optional Prometheus export (when prometheus-client is on classpath).
 *
 * Example:
 * <pre>
 * MetricsCollector collector = new MetricsCollector();
 * collector.setup();
 * // ... agent runs ...
 * String metrics = collector.export();  // Prometheus format
 * </pre>
 *
 * Metrics exposed:
 * - harness_loop_iterations_total: Total loop iterations
 * - harness_tool_calls_total: Total tool calls by tool name and success status
 * - harness_llm_tokens_total: Total token usage by type (input/output)
 * - harness_session_duration_seconds: Session duration in seconds
 * - harness_llm_call_duration_seconds: LLM call duration
 * - harness_tool_call_duration_seconds: Tool call duration by tool name
 */
public class MetricsCollector {

    private static final Logger logger = LoggerFactory.getLogger(MetricsCollector.class);

    private final MetricsConfig config;
    private boolean setupComplete = false;

    // Counters
    private final AtomicLong loopIterations = new AtomicLong(0);
    private final AtomicLong activeSessions = new AtomicLong(0);

    // Tool call counters (tool -> success -> count)
    private final ConcurrentHashMap<String, ConcurrentHashMap<Boolean, AtomicLong>> toolCalls = new ConcurrentHashMap<>();

    // Token counters
    private final AtomicLong inputTokens = new AtomicLong(0);
    private final AtomicLong outputTokens = new AtomicLong(0);
    private final AtomicLong cacheReadTokens = new AtomicLong(0);
    private final AtomicLong cacheWriteTokens = new AtomicLong(0);

    // Duration tracking
    private final ConcurrentHashMap<String, AtomicLong> toolDurations = new ConcurrentHashMap<>();
    private final AtomicLong llmDurationNanos = new AtomicLong(0);
    private final AtomicLong sessionDurationNanos = new AtomicLong(0);

    // Timing for sessions (using thread-local for simplicity)
    private final ThreadLocal<Instant> sessionStartTime = new ThreadLocal<>();
    private final ThreadLocal<Instant> llmCallStartTime = new ThreadLocal<>();
    private final ConcurrentHashMap<String, Instant> toolCallStartTimes = new ConcurrentHashMap<>();

    public MetricsCollector() {
        this(MetricsConfig.defaults());
    }

    public MetricsCollector(MetricsConfig config) {
        this.config = config;
    }

    /**
     * Check if metrics collection is enabled.
     */
    public boolean isEnabled() {
        return config.enabled();
    }

    /**
     * Set up metrics collection.
     *
     * @return True if setup was successful
     */
    public boolean setup() {
        if (!config.enabled()) {
            logger.debug("Metrics collection is disabled");
            return false;
        }

        if (setupComplete) {
            return true;
        }

        setupComplete = true;
        logger.info("Metrics collector initialized: prefix={}", config.prefix());
        return true;
    }

    /**
     * Export metrics in Prometheus format.
     *
     * @return Metrics data in Prometheus text format
     */
    public String export() {
        StringBuilder sb = new StringBuilder();
        String prefix = config.prefix();

        // Loop iterations
        sb.append("# TYPE ").append(prefix).append("_loop_iterations_total counter\n");
        sb.append(prefix).append("_loop_iterations_total ").append(loopIterations.get()).append("\n\n");

        // Tool calls
        sb.append("# TYPE ").append(prefix).append("_tool_calls_total counter\n");
        for (Map.Entry<String, ConcurrentHashMap<Boolean, AtomicLong>> entry : toolCalls.entrySet()) {
            String tool = entry.getKey();
            for (Map.Entry<Boolean, AtomicLong> status : entry.getValue().entrySet()) {
                sb.append(prefix).append("_tool_calls_total{tool=\"").append(tool)
                  .append("\",success=\"").append(status.getKey()).append("\"} ")
                  .append(status.getValue().get()).append("\n");
            }
        }
        sb.append("\n");

        // Token usage
        sb.append("# TYPE ").append(prefix).append("_llm_tokens_total counter\n");
        sb.append(prefix).append("_llm_tokens_total{type=\"input\"} ").append(inputTokens.get()).append("\n");
        sb.append(prefix).append("_llm_tokens_total{type=\"output\"} ").append(outputTokens.get()).append("\n");
        if (cacheReadTokens.get() > 0) {
            sb.append(prefix).append("_llm_tokens_total{type=\"cache_read\"} ").append(cacheReadTokens.get()).append("\n");
        }
        if (cacheWriteTokens.get() > 0) {
            sb.append(prefix).append("_llm_tokens_total{type=\"cache_write\"} ").append(cacheWriteTokens.get()).append("\n");
        }
        sb.append("\n");

        // Active sessions
        sb.append("# TYPE ").append(prefix).append("_active_sessions gauge\n");
        sb.append(prefix).append("_active_sessions ").append(activeSessions.get()).append("\n\n");

        // Session duration (cumulative)
        sb.append("# TYPE ").append(prefix).append("_session_duration_seconds_total counter\n");
        sb.append(prefix).append("_session_duration_seconds_total ").append(sessionDurationNanos.get() / 1_000_000_000.0).append("\n\n");

        // LLM call duration (cumulative)
        sb.append("# TYPE ").append(prefix).append("_llm_call_duration_seconds_total counter\n");
        sb.append(prefix).append("_llm_call_duration_seconds_total ").append(llmDurationNanos.get() / 1_000_000_000.0).append("\n\n");

        // Tool call durations
        sb.append("# TYPE ").append(prefix).append("_tool_call_duration_seconds_total counter\n");
        for (Map.Entry<String, AtomicLong> entry : toolDurations.entrySet()) {
            sb.append(prefix).append("_tool_call_duration_seconds_total{tool=\"").append(entry.getKey())
              .append("\"} ").append(entry.getValue().get() / 1_000_000_000.0).append("\n");
        }

        return sb.toString();
    }

    /**
     * Get the Prometheus content type.
     */
    public String getContentType() {
        return "text/plain; version=0.0.4; charset=utf-8";
    }

    // =========================================================================
    // Metric recording methods
    // =========================================================================

    /**
     * Record a loop iteration.
     */
    public void recordIteration() {
        loopIterations.incrementAndGet();
    }

    /**
     * Record a tool call.
     *
     * @param toolName        Name of the tool
     * @param success         Whether the call succeeded
     * @param durationSeconds Duration of the call (optional)
     */
    public void recordToolCall(String toolName, boolean success, Double durationSeconds) {
        toolCalls.computeIfAbsent(toolName, k -> new ConcurrentHashMap<>())
            .computeIfAbsent(success, k -> new AtomicLong(0))
            .incrementAndGet();

        if (durationSeconds != null) {
            toolDurations.computeIfAbsent(toolName, k -> new AtomicLong(0))
                .addAndGet((long) (durationSeconds * 1_000_000_000));
        }
    }

    /**
     * Record token usage.
     *
     * @param usage Token usage information
     */
    public void recordTokenUsage(TokenUsage usage) {
        inputTokens.addAndGet(usage.inputTokens());
        outputTokens.addAndGet(usage.outputTokens());

        if (usage.cacheReadTokens() > 0) {
            cacheReadTokens.addAndGet(usage.cacheReadTokens());
        }
        if (usage.cacheWriteTokens() > 0) {
            cacheWriteTokens.addAndGet(usage.cacheWriteTokens());
        }
    }

    /**
     * Record an LLM call duration.
     *
     * @param durationSeconds Duration of the LLM call
     */
    public void recordLlmCall(double durationSeconds) {
        llmDurationNanos.addAndGet((long) (durationSeconds * 1_000_000_000));
    }

    /**
     * Record session duration.
     *
     * @param durationSeconds Total session duration
     */
    public void recordSessionDuration(double durationSeconds) {
        sessionDurationNanos.addAndGet((long) (durationSeconds * 1_000_000_000));
    }

    /**
     * Increment active sessions count.
     */
    public void incrementActiveSessions() {
        activeSessions.incrementAndGet();
    }

    /**
     * Decrement active sessions count.
     */
    public void decrementActiveSessions() {
        activeSessions.decrementAndGet();
    }

    // =========================================================================
    // Progress event handler
    // =========================================================================

    /**
     * Create a progress event handler that records metrics.
     *
     * @return A consumer that can be passed to AgentHarness.run(onProgress=...)
     */
    public Consumer<ProgressEvent> createProgressHandler() {
        return event -> {
            String eventType = event.type().name();

            switch (eventType) {
                case "LOOP_START" -> {
                    sessionStartTime.set(Instant.now());
                    incrementActiveSessions();
                }
                case "LOOP_END" -> {
                    Instant start = sessionStartTime.get();
                    if (start != null) {
                        double duration = (Instant.now().toEpochMilli() - start.toEpochMilli()) / 1000.0;
                        recordSessionDuration(duration);
                        sessionStartTime.remove();
                    }
                    decrementActiveSessions();
                }
                case "ITERATION" -> recordIteration();
                case "LLM_CALL" -> llmCallStartTime.set(Instant.now());
                case "LLM_RESPONSE" -> {
                    Instant start = llmCallStartTime.get();
                    if (start != null) {
                        double duration = (Instant.now().toEpochMilli() - start.toEpochMilli()) / 1000.0;
                        recordLlmCall(duration);
                        llmCallStartTime.remove();
                    }
                    // Record token usage if available
                    if (event.data() != null && event.data().containsKey("token_usage")) {
                        Object usageData = event.data().get("token_usage");
                        if (usageData instanceof TokenUsage usage) {
                            recordTokenUsage(usage);
                        }
                    }
                }
                case "TOOL_CALL" -> {
                    String toolName = event.data() != null
                        ? (String) event.data().getOrDefault("tool", "unknown")
                        : "unknown";
                    toolCallStartTimes.put(toolName, Instant.now());
                }
                case "TOOL_RESULT" -> {
                    String toolName = event.data() != null
                        ? (String) event.data().getOrDefault("tool", "unknown")
                        : "unknown";
                    boolean success = event.data() != null
                        && Boolean.TRUE.equals(event.data().getOrDefault("success", true));

                    Instant start = toolCallStartTimes.remove(toolName);
                    Double duration = null;
                    if (start != null) {
                        duration = (Instant.now().toEpochMilli() - start.toEpochMilli()) / 1000.0;
                    }
                    recordToolCall(toolName, success, duration);
                }
            }
        };
    }

    /**
     * Get current metrics as a map.
     */
    public Map<String, Object> getMetrics() {
        Map<String, Object> metrics = new HashMap<>();
        metrics.put("loop_iterations", loopIterations.get());
        metrics.put("active_sessions", activeSessions.get());
        metrics.put("input_tokens", inputTokens.get());
        metrics.put("output_tokens", outputTokens.get());
        metrics.put("cache_read_tokens", cacheReadTokens.get());
        metrics.put("cache_write_tokens", cacheWriteTokens.get());
        metrics.put("session_duration_seconds", sessionDurationNanos.get() / 1_000_000_000.0);
        metrics.put("llm_call_duration_seconds", llmDurationNanos.get() / 1_000_000_000.0);
        return metrics;
    }

    /**
     * Reset all counters.
     */
    public void reset() {
        loopIterations.set(0);
        activeSessions.set(0);
        toolCalls.clear();
        inputTokens.set(0);
        outputTokens.set(0);
        cacheReadTokens.set(0);
        cacheWriteTokens.set(0);
        toolDurations.clear();
        llmDurationNanos.set(0);
        sessionDurationNanos.set(0);
        sessionStartTime.remove();
        llmCallStartTime.remove();
        toolCallStartTimes.clear();
    }
}
