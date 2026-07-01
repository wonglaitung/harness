package com.harness.orchestrator;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Monitoring service for orchestrator.
 *
 * <p>Provides unified observability:</p>
 * <ul>
 *   <li>Execution history: Track all workflow/team/goal executions</li>
 *   <li>Performance metrics: Duration, iterations, tokens</li>
 *   <li>Error tracking: Log and analyze failures</li>
 * </ul>
 *
 * <h2>Metrics Retention</h2>
 * <ul>
 *   <li>Keeps last N metrics in memory (configurable)</li>
 *   <li>Older metrics are automatically discarded</li>
 *   <li>For persistent storage, integrate with external systems</li>
 * </ul>
 */
public class ExecutionMonitor {
    private static final Logger logger = LoggerFactory.getLogger(ExecutionMonitor.class);

    private final int metricsRetention;
    private final List<ExecutionMetric> metrics = new ArrayList<>();
    private volatile boolean running = false;

    /**
     * Create a new ExecutionMonitor.
     *
     * @param metricsRetention Maximum number of metrics to retain
     */
    public ExecutionMonitor(int metricsRetention) {
        this.metricsRetention = metricsRetention;
    }

    /**
     * Create a new ExecutionMonitor with default retention.
     */
    public ExecutionMonitor() {
        this(1000);
    }

    /**
     * Start the monitor service.
     */
    public void start() {
        running = true;
        logger.info("Monitor service started");
    }

    /**
     * Stop the monitor service.
     */
    public void stop() {
        running = false;
        logger.info("Monitor service stopped");
    }

    /**
     * Record an execution metric.
     */
    public synchronized void record(ExecutionMetric metric) {
        metrics.add(metric);

        // Trim to retention limit
        while (metrics.size() > metricsRetention) {
            metrics.remove(0);
        }

        logger.debug("Recorded metric: {} ({}) - status={}, duration={:.2f}s",
                metric.getName(), metric.getType(), metric.getStatus(), metric.getDurationSeconds());
    }

    /**
     * Record a workflow execution.
     */
    public void recordWorkflow(String name, String status, double durationSeconds, int iterations, int tokensUsed) {
        record(ExecutionMetric.builder()
                .name(name)
                .type("workflow")
                .status(status)
                .durationSeconds(durationSeconds)
                .iterations(iterations)
                .tokensUsed(tokensUsed)
                .build());
    }

    /**
     * Record a team execution.
     */
    public void recordTeam(String name, String status, double durationSeconds, int iterations, int tokensUsed) {
        record(ExecutionMetric.builder()
                .name(name)
                .type("team")
                .status(status)
                .durationSeconds(durationSeconds)
                .iterations(iterations)
                .tokensUsed(tokensUsed)
                .build());
    }

    /**
     * Record a goal execution.
     */
    public void recordGoal(String name, String status, double durationSeconds, int iterations, int tokensUsed) {
        record(ExecutionMetric.builder()
                .name(name)
                .type("goal")
                .status(status)
                .durationSeconds(durationSeconds)
                .iterations(iterations)
                .tokensUsed(tokensUsed)
                .build());
    }

    /**
     * Get recorded metrics.
     *
     * @param limit       Maximum number of metrics to return
     * @param typeFilter  Filter by type ("workflow", "team", "goal"), or null for all
     */
    public synchronized List<ExecutionMetric> getMetrics(int limit, String typeFilter) {
        List<ExecutionMetric> filtered = metrics;
        if (typeFilter != null) {
            filtered = metrics.stream()
                    .filter(m -> m.getType().equals(typeFilter))
                    .collect(Collectors.toList());
        }

        int start = Math.max(0, filtered.size() - limit);
        return new ArrayList<>(filtered.subList(start, filtered.size()));
    }

    /**
     * Get all recorded metrics.
     */
    public List<ExecutionMetric> getMetrics() {
        return getMetrics(100, null);
    }

    /**
     * Get execution summary statistics.
     */
    public synchronized Map<String, Object> getSummary() {
        Map<String, Object> summary = new HashMap<>();

        if (metrics.isEmpty()) {
            summary.put("total_executions", 0);
            summary.put("success_rate", 0.0);
            summary.put("total_duration_seconds", 0.0);
            summary.put("total_tokens", 0);
            summary.put("average_duration", 0.0);
            return summary;
        }

        double totalDuration = metrics.stream().mapToDouble(ExecutionMetric::getDurationSeconds).sum();
        int totalTokens = metrics.stream().mapToInt(ExecutionMetric::getTokensUsed).sum();
        long successCount = metrics.stream().filter(m -> "success".equals(m.getStatus())).count();

        summary.put("total_executions", metrics.size());
        summary.put("success_rate", (double) successCount / metrics.size());
        summary.put("total_duration_seconds", totalDuration);
        summary.put("total_tokens", totalTokens);
        summary.put("average_duration", totalDuration / metrics.size());
        summary.put("by_type", getTypeBreakdown());

        return summary;
    }

    private Map<String, Map<String, Object>> getTypeBreakdown() {
        Map<String, Map<String, Object>> breakdown = new HashMap<>();

        for (String metricType : List.of("workflow", "team", "goal")) {
            List<ExecutionMetric> typeMetrics = metrics.stream()
                    .filter(m -> m.getType().equals(metricType))
                    .collect(Collectors.toList());

            if (!typeMetrics.isEmpty()) {
                long successCount = typeMetrics.stream()
                        .filter(m -> "success".equals(m.getStatus()))
                        .count();
                double totalDuration = typeMetrics.stream()
                        .mapToDouble(ExecutionMetric::getDurationSeconds)
                        .sum();
                int totalTokens = typeMetrics.stream()
                        .mapToInt(ExecutionMetric::getTokensUsed)
                        .sum();

                Map<String, Object> typeStats = new HashMap<>();
                typeStats.put("count", typeMetrics.size());
                typeStats.put("success_rate", (double) successCount / typeMetrics.size());
                typeStats.put("total_duration", totalDuration);
                typeStats.put("total_tokens", totalTokens);

                breakdown.put(metricType, typeStats);
            }
        }

        return breakdown;
    }

    /**
     * Get recent failed executions.
     */
    public synchronized List<ExecutionMetric> getRecentErrors(int limit) {
        return metrics.stream()
                .filter(m -> "failed".equals(m.getStatus()))
                .skip(Math.max(0, metrics.stream().filter(m -> "failed".equals(m.getStatus())).count() - limit))
                .collect(Collectors.toList());
    }

    /**
     * Get slowest executions.
     */
    public synchronized List<ExecutionMetric> getSlowest(int limit, String typeFilter) {
        List<ExecutionMetric> filtered = metrics;
        if (typeFilter != null) {
            filtered = metrics.stream()
                    .filter(m -> m.getType().equals(typeFilter))
                    .collect(Collectors.toList());
        }

        return filtered.stream()
                .sorted((a, b) -> Double.compare(b.getDurationSeconds(), a.getDurationSeconds()))
                .limit(limit)
                .collect(Collectors.toList());
    }

    /**
     * Clear all recorded metrics.
     */
    public synchronized void clearMetrics() {
        metrics.clear();
        logger.info("Metrics cleared");
    }

    /**
     * Check if monitor is running.
     */
    public boolean isRunning() {
        return running;
    }

    /**
     * Get number of recorded metrics.
     */
    public int getMetricCount() {
        return metrics.size();
    }
}
