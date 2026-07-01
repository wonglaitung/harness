package com.harness.orchestrator;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for ExecutionMonitor.
 */
class ExecutionMonitorTest {

    private ExecutionMonitor monitor;

    @BeforeEach
    void setUp() {
        monitor = new ExecutionMonitor(100);
    }

    @Test
    void testStartStop() {
        assertFalse(monitor.isRunning());

        monitor.start();
        assertTrue(monitor.isRunning());

        monitor.stop();
        assertFalse(monitor.isRunning());
    }

    @Test
    void testRecordMetric() {
        ExecutionMetric metric = ExecutionMetric.builder()
                .name("test")
                .type("workflow")
                .status("success")
                .durationSeconds(10.0)
                .build();

        monitor.record(metric);

        assertEquals(1, monitor.getMetricCount());
    }

    @Test
    void testRecordWorkflow() {
        monitor.recordWorkflow("my-workflow", "success", 30.0, 5, 500);

        List<ExecutionMetric> metrics = monitor.getMetrics();
        assertEquals(1, metrics.size());

        ExecutionMetric metric = metrics.get(0);
        assertEquals("my-workflow", metric.getName());
        assertEquals("workflow", metric.getType());
        assertEquals("success", metric.getStatus());
        assertEquals(30.0, metric.getDurationSeconds());
        assertEquals(5, metric.getIterations());
        assertEquals(500, metric.getTokensUsed());
    }

    @Test
    void testRecordTeam() {
        monitor.recordTeam("my-team", "success", 60.0, 10, 1000);

        List<ExecutionMetric> metrics = monitor.getMetrics();
        assertEquals(1, metrics.size());

        ExecutionMetric metric = metrics.get(0);
        assertEquals("my-team", metric.getName());
        assertEquals("team", metric.getType());
    }

    @Test
    void testRecordGoal() {
        monitor.recordGoal("my-goal", "failed", 15.0, 3, 200);

        List<ExecutionMetric> metrics = monitor.getMetrics();
        assertEquals(1, metrics.size());

        ExecutionMetric metric = metrics.get(0);
        assertEquals("my-goal", metric.getName());
        assertEquals("goal", metric.getType());
        assertEquals("failed", metric.getStatus());
    }

    @Test
    void testMetricsRetention() {
        ExecutionMonitor smallMonitor = new ExecutionMonitor(5);

        for (int i = 0; i < 10; i++) {
            smallMonitor.recordGoal("goal-" + i, "success", 1.0, 1, 100);
        }

        assertEquals(5, smallMonitor.getMetricCount());
    }

    @Test
    void testGetMetricsWithTypeFilter() {
        monitor.recordWorkflow("w1", "success", 10.0, 1, 100);
        monitor.recordTeam("t1", "success", 20.0, 2, 200);
        monitor.recordGoal("g1", "success", 5.0, 1, 50);

        List<ExecutionMetric> workflowMetrics = monitor.getMetrics(100, "workflow");
        assertEquals(1, workflowMetrics.size());
        assertEquals("w1", workflowMetrics.get(0).getName());

        List<ExecutionMetric> teamMetrics = monitor.getMetrics(100, "team");
        assertEquals(1, teamMetrics.size());
        assertEquals("t1", teamMetrics.get(0).getName());

        List<ExecutionMetric> allMetrics = monitor.getMetrics(100, null);
        assertEquals(3, allMetrics.size());
    }

    @Test
    void testGetSummary() {
        monitor.recordWorkflow("w1", "success", 10.0, 1, 100);
        monitor.recordWorkflow("w2", "failed", 20.0, 2, 200);
        monitor.recordGoal("g1", "success", 5.0, 1, 50);

        Map<String, Object> summary = monitor.getSummary();

        assertEquals(3, summary.get("total_executions"));
        assertEquals(2.0 / 3, (double) summary.get("success_rate"), 0.001);
        assertEquals(35.0, (double) summary.get("total_duration_seconds"), 0.001);
        assertEquals(350, summary.get("total_tokens"));

        @SuppressWarnings("unchecked")
        Map<String, Map<String, Object>> byType = (Map<String, Map<String, Object>>) summary.get("by_type");
        assertTrue(byType.containsKey("workflow"));
        assertTrue(byType.containsKey("goal"));
    }

    @Test
    void testGetSummaryEmpty() {
        Map<String, Object> summary = monitor.getSummary();

        assertEquals(0, summary.get("total_executions"));
        assertEquals(0.0, (double) summary.get("success_rate"), 0.001);
        assertEquals(0, summary.get("total_tokens"));
    }

    @Test
    void testGetRecentErrors() {
        monitor.recordWorkflow("w1", "success", 10.0, 1, 100);
        monitor.recordWorkflow("w2", "failed", 20.0, 2, 200);
        monitor.recordGoal("g1", "failed", 5.0, 1, 50);
        monitor.recordGoal("g2", "success", 5.0, 1, 50);

        List<ExecutionMetric> errors = monitor.getRecentErrors(10);
        assertEquals(2, errors.size());
    }

    @Test
    void testGetSlowest() {
        monitor.recordWorkflow("w1", "success", 10.0, 1, 100);
        monitor.recordWorkflow("w2", "success", 50.0, 2, 200);
        monitor.recordWorkflow("w3", "success", 30.0, 1, 100);

        List<ExecutionMetric> slowest = monitor.getSlowest(2, null);
        assertEquals(2, slowest.size());
        assertEquals("w2", slowest.get(0).getName());
        assertEquals("w3", slowest.get(1).getName());
    }

    @Test
    void testClearMetrics() {
        monitor.recordWorkflow("w1", "success", 10.0, 1, 100);
        assertEquals(1, monitor.getMetricCount());

        monitor.clearMetrics();
        assertEquals(0, monitor.getMetricCount());
    }
}
