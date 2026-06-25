package com.harness.core;

import java.util.Map;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for StepBudgetController.
 *
 * Reference: packages/sdk/tests/test_phase25_step_budget.py
 */
class StepBudgetControllerTest {

    // === StepBudgetConfig Tests ===

    @Test
    void testConfigDefaults() {
        StepBudgetConfig config = StepBudgetConfig.defaults();

        assertEquals(StepBudgetConfig.DEFAULT_MAX_ITERATIONS, config.maxIterationsPerTask());
        assertEquals(StepBudgetConfig.DEFAULT_MAX_TOOL_CALLS_PER_STEP, config.maxToolCallsPerStep());
        assertEquals(StepBudgetConfig.DEFAULT_MAX_TOOL_CALLS_PER_TASK, config.maxToolCallsPerTask());
        assertEquals(StepBudgetConfig.DEFAULT_WARNING_THRESHOLD, config.warningThreshold(), 0.001);
        assertEquals(StepBudgetConfig.DEFAULT_CRITICAL_THRESHOLD, config.criticalThreshold(), 0.001);
        assertEquals("stop", config.actionOnExceed());
    }

    @Test
    void testConfigCustomValues() {
        StepBudgetConfig config = StepBudgetConfig.builder()
            .maxIterationsPerTask(20)
            .maxToolCallsPerStep(5)
            .maxToolCallsPerTask(50)
            .warningThreshold(0.7)
            .criticalThreshold(0.9)
            .actionOnExceed("throttle")
            .throttleRatio(0.3)
            .build();

        assertEquals(20, config.maxIterationsPerTask());
        assertEquals(5, config.maxToolCallsPerStep());
        assertEquals(50, config.maxToolCallsPerTask());
        assertEquals(0.7, config.warningThreshold(), 0.001);
        assertEquals(0.9, config.criticalThreshold(), 0.001);
        assertEquals("throttle", config.actionOnExceed());
        assertEquals(0.3, config.throttleRatio(), 0.001);
    }

    @Test
    void testConfigDefaultConstructor() {
        StepBudgetConfig config = new StepBudgetConfig();

        assertEquals(50, config.maxIterationsPerTask());
        assertEquals(10, config.maxToolCallsPerStep());
        assertEquals(200, config.maxToolCallsPerTask());
    }

    // === StepUsage Tests ===

    @Test
    void testStepUsageDefaults() {
        StepUsage usage = new StepUsage();

        assertEquals(0, usage.iterations());
        assertEquals(0, usage.toolCallsTotal());
        assertEquals(0, usage.toolCallsThisStep());
        assertTrue(usage.toolCallsByTool().isEmpty());
    }

    @Test
    void testStepUsageIncrementIterations() {
        StepUsage usage = new StepUsage();
        usage = usage.incrementIterations();

        assertEquals(1, usage.iterations());
    }

    @Test
    void testStepUsageRecordToolCall() {
        StepUsage usage = new StepUsage();
        usage = usage.recordToolCall("read");
        usage = usage.recordToolCall("read");
        usage = usage.recordToolCall("write");

        assertEquals(3, usage.toolCallsTotal());
        assertEquals(3, usage.toolCallsThisStep());
        assertEquals(2, usage.toolCallsByTool().get("read"));
        assertEquals(1, usage.toolCallsByTool().get("write"));
    }

    @Test
    void testStepUsageResetStep() {
        StepUsage usage = new StepUsage();
        usage = usage.recordToolCall("read");
        usage = usage.recordToolCall("write");

        assertEquals(2, usage.toolCallsThisStep());

        usage = usage.resetStep();

        assertEquals(0, usage.toolCallsThisStep());
        assertEquals(2, usage.toolCallsTotal());  // Total should remain
    }

    @Test
    void testStepUsageToMap() {
        StepUsage usage = new StepUsage();
        usage = usage.incrementIterations();
        usage = usage.recordToolCall("read");

        Map<String, Object> map = usage.toMap();

        assertEquals(1, map.get("iterations"));
        assertEquals(1, map.get("toolCallsTotal"));
        assertEquals(1, map.get("toolCallsThisStep"));
        assertTrue(map.containsKey("taskStartTime"));
        assertTrue(map.containsKey("toolCallsByTool"));
    }

    // === BudgetCheckResult Tests ===

    @Test
    void testBudgetCheckResultNormal() {
        BudgetCheckResult result = BudgetCheckResult.normal("All good");

        assertEquals(BudgetLevel.NORMAL, result.level());
        assertTrue(result.isWithinBudget());
        assertEquals("All good", result.message());
        assertFalse(result.shouldStop());
        assertNull(result.throttleLimit());
    }

    @Test
    void testBudgetCheckResultExceeded() {
        BudgetCheckResult result = BudgetCheckResult.exceeded("Limit reached", true);

        assertEquals(BudgetLevel.EXCEEDED, result.level());
        assertFalse(result.isWithinBudget());
        assertEquals("Limit reached", result.message());
        assertTrue(result.shouldStop());
    }

    // === StepBudgetController Tests ===

    @Test
    void testControllerCreation() {
        StepBudgetController controller = new StepBudgetController();
        assertNotNull(controller);
    }

    @Test
    void testControllerWithConfig() {
        StepBudgetConfig config = StepBudgetConfig.builder()
            .maxIterationsPerTask(20)
            .build();
        StepBudgetController controller = new StepBudgetController(config);

        Map<String, Object> report = controller.getUsageReport();
        Map<String, Object> configMap = (Map<String, Object>) report.get("config");
        assertEquals(20, configMap.get("maxIterationsPerTask"));
    }

    @Test
    void testStartAndEndTask() {
        StepBudgetController controller = new StepBudgetController();

        controller.startTask();
        StepUsage usage = controller.endTask();

        assertNotNull(usage);
        assertEquals(0, usage.iterations());
    }

    @Test
    void testAdvanceIteration() {
        StepBudgetController controller = new StepBudgetController();
        controller.startTask();

        BudgetCheckResult result = controller.advanceIteration();

        assertTrue(result.isWithinBudget());
        assertEquals(1, controller.getUsage().iterations());
    }

    @Test
    void testRecordToolCall() {
        StepBudgetController controller = new StepBudgetController();
        controller.startTask();

        BudgetCheckResult result = controller.recordToolCall("read");

        assertTrue(result.isWithinBudget());
        assertEquals(1, controller.getUsage().toolCallsTotal());
        assertEquals(1, controller.getUsage().toolCallsByTool().get("read"));
    }

    @Test
    void testCheckBeforeToolCall() {
        StepBudgetController controller = new StepBudgetController();
        controller.startTask();

        BudgetCheckResult result = controller.checkBeforeToolCall("read");

        assertTrue(result.isWithinBudget());
        // Should NOT increment counter (just a check)
        assertEquals(0, controller.getUsage().toolCallsTotal());
    }

    @Test
    void testStepLimitExceeded() {
        StepBudgetConfig config = StepBudgetConfig.builder()
            .maxToolCallsPerStep(2)
            .actionOnExceed("stop")
            .build();
        StepBudgetController controller = new StepBudgetController(config);
        controller.startTask();

        controller.recordToolCall("read");
        controller.recordToolCall("write");
        BudgetCheckResult result = controller.checkBeforeToolCall("bash");

        assertFalse(result.isWithinBudget());
        assertTrue(result.shouldStop());
    }

    @Test
    void testTotalLimitExceeded() {
        StepBudgetConfig config = StepBudgetConfig.builder()
            .maxToolCallsPerTask(3)
            .actionOnExceed("stop")
            .build();
        StepBudgetController controller = new StepBudgetController(config);
        controller.startTask();

        controller.recordToolCall("read");
        controller.recordToolCall("write");
        controller.recordToolCall("bash");
        BudgetCheckResult result = controller.checkBeforeToolCall("read");

        assertFalse(result.isWithinBudget());
    }

    @Test
    void testIterationLimitExceeded() {
        StepBudgetConfig config = StepBudgetConfig.builder()
            .maxIterationsPerTask(3)
            .actionOnExceed("stop")
            .build();
        StepBudgetController controller = new StepBudgetController(config);
        controller.startTask();

        controller.advanceIteration();
        controller.advanceIteration();
        controller.advanceIteration();
        BudgetCheckResult result = controller.advanceIteration();

        assertFalse(result.isWithinBudget());
        assertTrue(result.shouldStop());
    }

    @Test
    void testWarningThreshold() {
        StepBudgetConfig config = StepBudgetConfig.builder()
            .maxIterationsPerTask(10)
            .warningThreshold(0.8)
            .build();
        StepBudgetController controller = new StepBudgetController(config);
        controller.startTask();

        // 8 iterations = 80% (warning threshold)
        for (int i = 0; i < 8; i++) {
            controller.advanceIteration();
        }
        BudgetCheckResult result = controller.advanceIteration();

        assertEquals(BudgetLevel.WARNING, result.level());
    }

    @Test
    void testThrottleAction() {
        StepBudgetConfig config = StepBudgetConfig.builder()
            .maxToolCallsPerTask(5)
            .actionOnExceed("throttle")
            .throttleRatio(0.5)
            .build();
        StepBudgetController controller = new StepBudgetController(config);
        controller.startTask();

        // Exhaust budget
        for (int i = 0; i < 5; i++) {
            controller.recordToolCall("tool" + i);
        }
        BudgetCheckResult result = controller.checkBeforeToolCall("read");

        // With throttle, should not stop but provide throttle limit
        assertFalse(result.shouldStop());
        // throttleLimit should be set
        assertNotNull(result.throttleLimit());
    }

    @Test
    void testGetUsageReport() {
        StepBudgetController controller = new StepBudgetController();
        controller.startTask();

        controller.advanceIteration();
        controller.recordToolCall("read");
        controller.recordToolCall("write");

        Map<String, Object> report = controller.getUsageReport();

        assertTrue(report.containsKey("iterations"));
        assertTrue(report.containsKey("toolCalls"));
        assertTrue(report.containsKey("config"));
        assertTrue(report.containsKey("taskActive"));

        Map<String, Object> iterations = (Map<String, Object>) report.get("iterations");
        assertEquals(1, iterations.get("used"));

        Map<String, Object> toolCalls = (Map<String, Object>) report.get("toolCalls");
        assertEquals(2, toolCalls.get("used"));
    }

    @Test
    void testOperationsWithoutActiveTask() {
        StepBudgetController controller = new StepBudgetController();

        // Should handle gracefully without active task
        BudgetCheckResult result1 = controller.advanceIteration();
        BudgetCheckResult result2 = controller.recordToolCall("read");
        BudgetCheckResult result3 = controller.checkBeforeToolCall("read");

        // Should return normal results but not crash
        assertNotNull(result1);
        assertNotNull(result2);
        assertNotNull(result3);
    }

    @Test
    void testResetStepOnAdvanceIteration() {
        StepBudgetController controller = new StepBudgetController();
        controller.startTask();

        controller.recordToolCall("read");
        controller.recordToolCall("write");
        assertEquals(2, controller.getUsage().toolCallsThisStep());

        controller.advanceIteration();

        // Step counter should reset
        assertEquals(0, controller.getUsage().toolCallsThisStep());
        // Total should remain
        assertEquals(2, controller.getUsage().toolCallsTotal());
    }
}
