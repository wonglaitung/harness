package com.harness.core;

import java.util.Map;

import com.harness.types.CostConfig;
import com.harness.types.TokenUsage;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for CostController.
 *
 * Reference: packages/sdk/tests/test_cost_control.py
 */
class CostControllerTest {

    // === CostConfig Tests ===

    @Test
    void testCostConfigDefaults() {
        CostConfig config = CostConfig.defaults();

        assertEquals(CostConfig.DEFAULT_MAX_TOKENS_PER_SESSION, config.maxTokensPerSession());
        assertEquals(CostConfig.DEFAULT_MAX_TOOL_CALLS_PER_SESSION, config.maxToolCallsPerSession());
        assertEquals(CostConfig.DEFAULT_MAX_ITERATIONS_PER_REQUEST, config.maxIterationsPerRequest());
        assertEquals(CostConfig.DEFAULT_WARNING_THRESHOLD, config.warningThreshold(), 0.001);
        assertEquals("stop", config.actionOnExceed());
    }

    @Test
    void testCostConfigCustomValues() {
        CostConfig config = CostConfig.builder()
            .maxTokensPerSession(100_000)
            .maxToolCallsPerSession(100)
            .warningThreshold(0.9)
            .actionOnExceed("compress")
            .build();

        assertEquals(100_000, config.maxTokensPerSession());
        assertEquals(100, config.maxToolCallsPerSession());
        assertEquals(0.9, config.warningThreshold(), 0.001);
        assertEquals("compress", config.actionOnExceed());
    }

    @Test
    void testCostConfigInvalidActionOnExceed() {
        assertThrows(IllegalArgumentException.class, () -> {
            CostConfig.builder()
                .actionOnExceed("invalid")
                .build();
        });
    }

    @Test
    void testCostConfigValidActions() {
        for (String action : new String[]{"stop", "compress", "warn", "downgrade"}) {
            CostConfig config = CostConfig.builder()
                .actionOnExceed(action)
                .build();
            assertEquals(action, config.actionOnExceed());
        }
    }

    // === TokenUsage Tests ===

    @Test
    void testTokenUsageCreation() {
        TokenUsage usage = new TokenUsage(100, 50);
        assertEquals(100, usage.inputTokens());
        assertEquals(50, usage.outputTokens());
        assertEquals(150, usage.totalTokens());
    }

    @Test
    void testTokenUsageDefaultCreation() {
        TokenUsage usage = new TokenUsage();
        assertEquals(0, usage.inputTokens());
        assertEquals(0, usage.outputTokens());
        assertEquals(0, usage.toolCalls());
    }

    @Test
    void testTokenUsageAdd() {
        TokenUsage a = new TokenUsage(100, 50);
        TokenUsage b = new TokenUsage(200, 100);
        TokenUsage c = a.add(b);

        assertEquals(300, c.inputTokens());
        assertEquals(150, c.outputTokens());
    }

    @Test
    void testTokenUsageBuilder() {
        TokenUsage usage = TokenUsage.builder()
            .inputTokens(100)
            .outputTokens(50)
            .toolCalls(5)
            .build();

        assertEquals(100, usage.inputTokens());
        assertEquals(50, usage.outputTokens());
        assertEquals(5, usage.toolCalls());
    }

    @Test
    void testTokenUsageCheckBudgetWithinLimit() {
        TokenUsage usage = new TokenUsage(500, 100);
        CostConfig config = CostConfig.defaults();

        Object[] result = usage.checkBudget(config);
        boolean isWithin = (boolean) result[0];
        String warning = (String) result[1];

        assertTrue(isWithin);
        assertNull(warning);
    }

    @Test
    void testTokenUsageCheckBudgetExceeded() {
        TokenUsage usage = TokenUsage.builder()
            .inputTokens(1_500_000)
            .outputTokens(100)
            .build();
        CostConfig config = CostConfig.defaults();

        Object[] result = usage.checkBudget(config);
        boolean isWithin = (boolean) result[0];
        String warning = (String) result[1];

        assertFalse(isWithin);
        assertNotNull(warning);
        assertTrue(warning.contains("Token budget exceeded"));
    }

    @Test
    void testTokenUsageCheckBudgetWarning() {
        TokenUsage usage = TokenUsage.builder()
            .inputTokens(850_000)
            .outputTokens(0)
            .build();
        CostConfig config = CostConfig.defaults();

        Object[] result = usage.checkBudget(config);
        boolean isWithin = (boolean) result[0];
        String warning = (String) result[1];

        assertTrue(isWithin);
        assertNotNull(warning);
        assertTrue(warning.contains("Token usage"));
    }

    @Test
    void testTokenUsageCheckToolCallLimit() {
        TokenUsage usage = TokenUsage.builder()
            .toolCalls(600)
            .build();
        CostConfig config = CostConfig.defaults();

        Object[] result = usage.checkBudget(config);
        boolean isWithin = (boolean) result[0];
        String warning = (String) result[1];

        assertFalse(isWithin);
        assertTrue(warning.contains("Tool call budget exceeded"));
    }

    // === CostController Tests ===

    @Test
    void testControllerDefaultInit() {
        CostController controller = new CostController();
        assertNotNull(controller);
        assertEquals(CostConfig.DEFAULT_MAX_TOKENS_PER_SESSION,
            controller.getSessionUsage("test").totalTokens());
    }

    @Test
    void testControllerCustomConfig() {
        CostConfig config = CostConfig.builder()
            .maxTokensPerSession(100_000)
            .build();
        CostController controller = new CostController(config);

        Map<String, Object> stats = controller.getStats();
        Map<String, Object> configMap = (Map<String, Object>) stats.get("config");
        assertEquals(100_000, configMap.get("maxTokensPerSession"));
    }

    @Test
    void testControllerCheckWithinBudget() {
        CostController controller = new CostController();
        TokenUsage usage = new TokenUsage(100, 50);

        BudgetStatus status = controller.check(usage, "test-session");

        assertTrue(status.isWithinBudget());
        assertNull(status.getWarningMessage());
    }

    @Test
    void testControllerCheckExceededBudget() {
        CostConfig config = CostConfig.builder()
            .maxTokensPerSession(100)
            .build();
        CostController controller = new CostController(config);
        TokenUsage usage = new TokenUsage(150, 0);

        BudgetStatus status = controller.check(usage, "test-session");

        assertFalse(status.isWithinBudget());
        assertNotNull(status.getWarningMessage());
        assertTrue(status.getWarningMessage().contains("Token budget exceeded"));
    }

    @Test
    void testControllerCheckWithCompressAction() {
        CostConfig config = CostConfig.builder()
            .maxTokensPerSession(100)
            .actionOnExceed("compress")
            .build();
        CostController controller = new CostController(config);
        TokenUsage usage = new TokenUsage(150, 0);

        BudgetStatus status = controller.check(usage, "test-session");

        // With compress action, should continue but flag compression
        assertTrue(status.isWithinBudget());
        assertTrue(status.shouldCompress());
    }

    @Test
    void testControllerCheckIterationWithinLimit() {
        CostController controller = new CostController();

        assertTrue(controller.checkIteration(10, "test-session"));
    }

    @Test
    void testControllerCheckIterationExceeded() {
        CostConfig config = CostConfig.builder()
            .maxIterationsPerRequest(20)
            .build();
        CostController controller = new CostController(config);

        assertFalse(controller.checkIteration(20, "test-session"));
    }

    @Test
    void testControllerRecordUsage() {
        CostController controller = new CostController();

        TokenUsage usage = controller.recordUsage("test-session", 100, 50, true, null, 0.0);

        assertEquals(100, usage.inputTokens());
        assertEquals(50, usage.outputTokens());
        assertEquals(1, usage.toolCalls());
    }

    @Test
    void testControllerRecordUsageAccumulates() {
        CostController controller = new CostController();

        controller.recordUsage("test-session", 100, 50, false, null, 0.0);
        controller.recordUsage("test-session", 50, 25, true, null, 0.0);

        TokenUsage usage = controller.getSessionUsage("test-session");

        assertEquals(150, usage.inputTokens());
        assertEquals(75, usage.outputTokens());
        assertEquals(1, usage.toolCalls());
    }

    @Test
    void testControllerGetSessionUsageUnknown() {
        CostController controller = new CostController();

        TokenUsage usage = controller.getSessionUsage("unknown-session");

        assertEquals(0, usage.inputTokens());
        assertEquals(0, usage.outputTokens());
    }

    @Test
    void testControllerResetSession() {
        CostController controller = new CostController();

        controller.recordUsage("test-session", 100, 50, false, null, 0.0);
        controller.resetSession("test-session");

        TokenUsage usage = controller.getSessionUsage("test-session");

        assertEquals(0, usage.inputTokens());
        assertEquals(0, usage.outputTokens());
    }

    @Test
    void testControllerShouldStop() {
        CostConfig config = CostConfig.builder()
            .maxTokensPerSession(100)
            .actionOnExceed("stop")
            .build();
        CostController controller = new CostController(config);
        TokenUsage usage = new TokenUsage(150, 0);

        assertTrue(controller.shouldStop(usage));
    }

    @Test
    void testControllerShouldStopWithCompress() {
        CostConfig config = CostConfig.builder()
            .maxTokensPerSession(100)
            .actionOnExceed("compress")
            .build();
        CostController controller = new CostController(config);
        TokenUsage usage = new TokenUsage(150, 0);

        // With compress, should not stop
        assertFalse(controller.shouldStop(usage));
    }

    @Test
    void testControllerShouldCompress() {
        CostConfig config = CostConfig.builder()
            .maxTokensPerSession(100)
            .actionOnExceed("compress")
            .build();
        CostController controller = new CostController(config);
        TokenUsage usage = new TokenUsage(150, 0);

        assertTrue(controller.shouldCompress(usage));
    }

    @Test
    void testControllerStats() {
        CostController controller = new CostController();
        controller.recordUsage("test-session", 100, 50, false, null, 0.0);

        Map<String, Object> stats = controller.getStats();

        assertTrue(stats.containsKey("config"));
        assertTrue(stats.containsKey("sessionsTracked"));
        assertEquals(1, stats.get("sessionsTracked"));
    }

    // === BudgetStatus Tests ===

    @Test
    void testBudgetStatusIsWarning() {
        BudgetStatus status = new BudgetStatus(
            true, new TokenUsage(), CostConfig.defaults(), "Budget warning", false, false, 0.8
        );

        assertTrue(status.isWarning());
    }

    @Test
    void testBudgetStatusIsNotWarningWhenExceeded() {
        BudgetStatus status = new BudgetStatus(
            false, new TokenUsage(), CostConfig.defaults(), "Budget exceeded", false, false, 1.0
        );

        assertFalse(status.isWarning());
    }

    @Test
    void testBudgetStatusRemainingTokens() {
        TokenUsage usage = new TokenUsage(300, 200);
        CostConfig config = CostConfig.builder()
            .maxTokensPerSession(1_000_000)
            .build();

        BudgetStatus status = new BudgetStatus(true, usage, config, null, false, false, 0.0005);

        assertEquals(999_500, status.getRemainingTokens());
    }

    @Test
    void testBudgetStatusRemainingToolCalls() {
        TokenUsage usage = TokenUsage.builder()
            .toolCalls(50)
            .build();
        CostConfig config = CostConfig.builder()
            .maxToolCallsPerSession(500)
            .build();

        BudgetStatus status = new BudgetStatus(true, usage, config, null, false, false, 0.0);

        assertEquals(450, status.getRemainingToolCalls());
    }
}
