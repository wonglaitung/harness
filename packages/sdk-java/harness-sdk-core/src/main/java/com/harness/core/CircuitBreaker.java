package com.harness.core;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Circuit breaker to detect and prevent infinite loops.
 *
 * Simple approach:
 * - Detect when same tool is called with same arguments repeatedly
 * - Detect when too many errors occur in a short time
 *
 * We don't try to be "smart" about detecting complex patterns.
 * Trust the model (via system prompt) to know when to stop.
 *
 * Example:
 * <pre>
 * CircuitBreaker cb = new CircuitBreaker();
 *
 * // Before tool execution
 * if (cb.isOpen()) {
 *     throw new CircuitBreakerException(cb.getReason());
 * }
 *
 * // Record call
 * cb.recordCall("read", Map.of("path", "/tmp/file.txt"));
 *
 * // On error
 * cb.recordError(e);
 *
 * // On success
 * cb.recordSuccess();
 * </pre>
 */
public class CircuitBreaker {

    private static final Logger logger = LoggerFactory.getLogger(CircuitBreaker.class);

    private final CircuitBreakerConfig config;
    private CircuitState state = CircuitState.CLOSED;

    // Track tool:args combination (simple and effective)
    private final Map<String, Integer> toolArgsCounter = new HashMap<>();

    // Track errors
    private final List<Instant> errorTimes = new ArrayList<>();

    // Track half-open state
    private Instant openTime = null;
    private int halfOpenCalls = 0;

    // Track why circuit opened
    private String openReason = null;

    public CircuitBreaker() {
        this(CircuitBreakerConfig.defaults());
    }

    public CircuitBreaker(CircuitBreakerConfig config) {
        this.config = config;
    }

    /**
     * Record a tool call for pattern detection.
     *
     * Simple: just count tool:args combinations.
     */
    public void recordCall(String toolName, Map<String, Object> arguments) {
        String argsKey = makeArgsKey(toolName, arguments);
        toolArgsCounter.merge(argsKey, 1, Integer::sum);

        // Check if we should open circuit
        checkPatterns();
    }

    /**
     * Record an error during tool execution.
     */
    public void recordError(Exception error) {
        errorTimes.add(Instant.now());

        // Clean old errors outside window
        Instant cutoff = Instant.now().minus(config.errorWindowSeconds(), ChronoUnit.SECONDS);
        errorTimes.removeIf(t -> t.isBefore(cutoff));

        // Check if error threshold reached
        if (errorTimes.size() >= config.errorThreshold()) {
            openReason = String.format("%d errors in last %d seconds",
                errorTimes.size(), config.errorWindowSeconds());
            open();
        }
    }

    /**
     * Record a successful tool execution.
     */
    public void recordSuccess() {
        if (state == CircuitState.HALF_OPEN) {
            close();
        }
    }

    /**
     * Check if circuit is open (should block calls).
     */
    public boolean isOpen() {
        if (state == CircuitState.CLOSED) {
            return false;
        }

        if (state == CircuitState.OPEN) {
            if (openTime != null) {
                long elapsed = ChronoUnit.SECONDS.between(openTime, Instant.now());
                if (elapsed >= config.recoveryTimeoutSeconds()) {
                    halfOpen();
                    return false;
                }
            }
            return true;
        }

        // HALF_OPEN state
        if (halfOpenCalls >= config.halfOpenMaxCalls()) {
            return true;
        }

        return false;
    }

    /**
     * Get the reason why circuit is open.
     */
    public String getReason() {
        if (state == CircuitState.CLOSED) {
            return null;
        }
        return openReason != null ? openReason : "Circuit breaker is open";
    }

    /**
     * Reset the circuit breaker to closed state.
     */
    public void reset() {
        close();
        toolArgsCounter.clear();
        errorTimes.clear();
        openReason = null;
    }

    /**
     * Get current circuit state.
     */
    public CircuitState getState() {
        return state;
    }

    /**
     * Get circuit breaker statistics.
     */
    public Map<String, Object> getStats() {
        Map<String, Object> stats = new LinkedHashMap<>();
        stats.put("state", state.name());
        stats.put("recentErrors", errorTimes.size());

        // Get top 5 most common tool:args combinations
        Map<String, Integer> topCalls = new LinkedHashMap<>();
        toolArgsCounter.entrySet().stream()
            .sorted(Map.Entry.<String, Integer>comparingByValue().reversed())
            .limit(5)
            .forEach(e -> topCalls.put(e.getKey(), e.getValue()));
        stats.put("toolArgsCounter", topCalls);

        return stats;
    }

    // === Private Methods ===

    private void checkPatterns() {
        // Only check: same tool + same args repeated
        for (Map.Entry<String, Integer> entry : toolArgsCounter.entrySet()) {
            if (entry.getValue() >= config.sameArgsThreshold()) {
                String toolName = entry.getKey().split(":", 2)[0];
                openReason = String.format(
                    "Tool '%s' with same arguments called %d times (threshold: %d)",
                    toolName, entry.getValue(), config.sameArgsThreshold()
                );
                logger.warn("Circuit breaker opening: {}", openReason);
                open();
                return;
            }
        }
    }

    private String makeArgsKey(String toolName, Map<String, Object> arguments) {
        String argsHash = hashableArgs(arguments);
        return toolName + ":" + argsHash;
    }

    private String hashableArgs(Map<String, Object> args) {
        if (args == null || args.isEmpty()) {
            return "{}";
        }

        // Simple string representation for hashing
        StringBuilder sb = new StringBuilder();
        sb.append("{");
        boolean first = true;
        for (Map.Entry<String, Object> entry : args.entrySet()) {
            if (!first) sb.append(",");
            first = false;
            sb.append(entry.getKey());
            sb.append("=");
            Object value = entry.getValue();
            if (value instanceof Map) {
                sb.append(hashableArgs((Map<String, Object>) value));
            } else if (value instanceof List) {
                sb.append(value.toString());
            } else {
                sb.append(value != null ? value.toString() : "null");
            }
        }
        sb.append("}");
        return sb.toString();
    }

    private void open() {
        state = CircuitState.OPEN;
        openTime = Instant.now();
        halfOpenCalls = 0;
    }

    private void halfOpen() {
        state = CircuitState.HALF_OPEN;
        halfOpenCalls = 0;
        logger.info("Circuit breaker entering half-open state");
    }

    private void close() {
        state = CircuitState.CLOSED;
        openTime = null;
        halfOpenCalls = 0;
        logger.info("Circuit breaker closed");
    }
}
