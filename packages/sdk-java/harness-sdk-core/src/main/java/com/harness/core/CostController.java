package com.harness.core;

import java.util.HashMap;
import java.util.Map;
import java.util.function.Consumer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.types.CostConfig;
import com.harness.types.ProgressEvent;
import com.harness.types.ProgressEventType;
import com.harness.types.TokenUsage;

/**
 * Controller for managing multi-level budgets.
 *
 * Enforces limits on:
 * - Session level: tokens, tool calls, iterations
 * - User level: daily tokens, hourly requests
 * - Global level: daily budget in USD
 *
 * Emits warnings at configurable threshold (default 80%).
 *
 * Example:
 * <pre>
 * CostConfig config = CostConfig.builder()
 *     .maxTokensPerSession(100_000)
 *     .build();
 * CostController controller = new CostController(config);
 *
 * // Check before operation
 * BudgetStatus status = controller.check(usage);
 * if (!status.isWithinBudget()) {
 *     throw new BudgetExceededException(status.getWarningMessage());
 * }
 * </pre>
 */
public class CostController {

    private static final Logger logger = LoggerFactory.getLogger(CostController.class);

    private final CostConfig config;
    private final CostStorage storage;
    private final Consumer<ProgressEvent> onProgress;

    // Session tracking
    private final Map<String, TokenUsage> sessionUsage = new HashMap<>();
    private final Map<String, Integer> requestIterations = new HashMap<>();

    // Global usage (in-memory)
    private final GlobalUsage globalUsage = new GlobalUsage();

    // User usage cache (in-memory, should be backed by storage)
    private final Map<String, UserUsage> userUsageCache = new HashMap<>();

    /**
     * Interface for cost storage backend.
     */
    public interface CostStorage {
        UserUsage getUserUsage(String userId);
        void recordUserUsage(String userId, int inputTokens, int outputTokens, boolean request);
        GlobalUsage getGlobalUsage();
        void recordGlobalUsage(double costUsd, int tokens);
    }

    public CostController() {
        this(CostConfig.defaults(), null, null);
    }

    public CostController(CostConfig config) {
        this(config, null, null);
    }

    public CostController(CostConfig config, CostStorage storage, Consumer<ProgressEvent> onProgress) {
        this.config = config;
        this.storage = storage;
        this.onProgress = onProgress;
    }

    /**
     * Check if usage is within budget.
     */
    public BudgetStatus check(TokenUsage usage, String sessionId) {
        Object[] result = usage.checkBudget(config);
        boolean isWithin = (boolean) result[0];
        String warning = (String) result[1];
        double usageRatio = (double) usage.totalTokens() / config.maxTokensPerSession();

        boolean shouldCompress = false;
        boolean shouldDowngrade = false;

        if (!isWithin) {
            if ("compress".equals(config.actionOnExceed())) {
                shouldCompress = true;
                isWithin = true;
            } else if ("downgrade".equals(config.actionOnExceed())) {
                shouldDowngrade = true;
                isWithin = true;
            }
        }

        BudgetStatus status = new BudgetStatus(
            isWithin, usage, config, warning, shouldCompress, shouldDowngrade, usageRatio
        );

        // Emit progress event for warnings
        if (warning != null && onProgress != null) {
            ProgressEventType eventType = !isWithin ? ProgressEventType.ERROR : ProgressEventType.STATE_CHANGE;
            onProgress.accept(ProgressEvent.of(
                eventType,
                warning,
                Map.of(
                    "usageRatio", usageRatio,
                    "totalTokens", usage.totalTokens(),
                    "limit", config.maxTokensPerSession()
                )
            ));
        }

        return status;
    }

    /**
     * Check user-level budget.
     */
    public UserBudgetStatus checkUserBudget(String userId) {
        UserUsage usage;
        if (storage != null) {
            usage = storage.getUserUsage(userId);
        } else {
            usage = userUsageCache.computeIfAbsent(userId, UserUsage::new);
        }

        Object[] result = usage.checkBudget(config);
        boolean isWithin = (boolean) result[0];
        String warning = (String) result[1];
        double usageRatio = config.dailyTokenLimit() > 0
            ? (double) usage.getDailyTokens() / config.dailyTokenLimit()
            : 0;

        return new UserBudgetStatus(isWithin, usage, config, warning, usageRatio);
    }

    /**
     * Check global budget.
     */
    public GlobalBudgetStatus checkGlobalBudget() {
        GlobalUsage usage = storage != null ? storage.getGlobalUsage() : globalUsage;

        double usageRatio = config.globalDailyBudgetUsd() > 0
            ? usage.getDailyCostUsd() / config.globalDailyBudgetUsd()
            : 0;

        boolean isWithin = usage.getDailyCostUsd() < config.globalDailyBudgetUsd();
        boolean shouldThrottle = config.autoThrottle() && usageRatio >= 0.8;

        String warning = null;
        if (!isWithin) {
            warning = String.format("Global budget exceeded: $%.2f/$%.2f",
                usage.getDailyCostUsd(), config.globalDailyBudgetUsd());
        } else if (shouldThrottle) {
            warning = String.format("Global budget warning: %.0f%% of daily budget used", usageRatio * 100);
        }

        return new GlobalBudgetStatus(isWithin, usage.getDailyCostUsd(), config.globalDailyBudgetUsd(),
            warning, shouldThrottle);
    }

    /**
     * Check all budget levels.
     */
    public BudgetCheckResult checkAll(TokenUsage usage, String sessionId, String userId) {
        BudgetStatus sessionStatus = check(usage, sessionId);
        UserBudgetStatus userStatus = userId != null ? checkUserBudget(userId) : null;
        GlobalBudgetStatus globalStatus = checkGlobalBudget();

        return new BudgetCheckResult(sessionStatus, userStatus, globalStatus);
    }

    /**
     * Check if iteration count is within limit.
     */
    public boolean checkIteration(int iteration, String sessionId) {
        if (iteration >= config.maxIterationsPerRequest()) {
            logger.warn("Iteration limit reached: {}/{}", iteration, config.maxIterationsPerRequest());
            return false;
        }
        return true;
    }

    /**
     * Record usage for a session.
     */
    public TokenUsage recordUsage(String sessionId, int inputTokens, int outputTokens,
                                   boolean toolCall, String userId, double costUsd) {
        TokenUsage usage = sessionUsage.computeIfAbsent(sessionId, k -> new TokenUsage());

        usage = usage.addInputTokens(inputTokens);
        usage = usage.addOutputTokens(outputTokens);
        if (toolCall) {
            usage = usage.addToolCall();
        }
        sessionUsage.put(sessionId, usage);

        // Record user-level usage
        if (storage != null && userId != null) {
            storage.recordUserUsage(userId, inputTokens, outputTokens, true);
        } else if (userId != null) {
            UserUsage userUsage = userUsageCache.computeIfAbsent(userId, UserUsage::new);
            userUsage.addTokens(inputTokens + outputTokens);
            userUsage.addRequest();
        }

        // Record global usage
        if (storage != null && costUsd > 0) {
            storage.recordGlobalUsage(costUsd, inputTokens + outputTokens);
        } else if (costUsd > 0) {
            globalUsage.addCost(costUsd);
            globalUsage.addTokens(inputTokens + outputTokens);
        }

        return usage;
    }

    /**
     * Get usage for a session.
     */
    public TokenUsage getSessionUsage(String sessionId) {
        return sessionUsage.getOrDefault(sessionId, new TokenUsage());
    }

    /**
     * Reset usage tracking for a session.
     */
    public void resetSession(String sessionId) {
        sessionUsage.remove(sessionId);
        requestIterations.remove(sessionId);
    }

    /**
     * Check if execution should stop due to budget.
     */
    public boolean shouldStop(TokenUsage usage) {
        BudgetStatus status = check(usage, null);
        return !status.isWithinBudget() && !status.shouldCompress();
    }

    /**
     * Check if context should be compressed.
     */
    public boolean shouldCompress(TokenUsage usage) {
        BudgetStatus status = check(usage, null);
        return status.shouldCompress();
    }

    /**
     * Check if model should be downgraded.
     */
    public boolean shouldDowngrade(TokenUsage usage) {
        BudgetStatus status = check(usage, null);
        return status.shouldDowngrade();
    }

    /**
     * Get the fallback model for budget-constrained scenarios.
     */
    public String getFallbackModel() {
        return config.fallbackModel();
    }

    /**
     * Get controller statistics.
     */
    public Map<String, Object> getStats() {
        Map<String, Object> configMap = new HashMap<>();
        configMap.put("maxTokensPerSession", config.maxTokensPerSession());
        configMap.put("maxToolCallsPerSession", config.maxToolCallsPerSession());
        configMap.put("maxIterationsPerRequest", config.maxIterationsPerRequest());
        configMap.put("dailyTokenLimit", config.dailyTokenLimit());
        configMap.put("hourlyRequestLimit", config.hourlyRequestLimit());
        configMap.put("globalDailyBudgetUsd", config.globalDailyBudgetUsd());
        configMap.put("warningThreshold", config.warningThreshold());

        Map<String, Object> stats = new HashMap<>();
        stats.put("config", configMap);
        stats.put("sessionsTracked", sessionUsage.size());
        stats.put("storageEnabled", storage != null);
        return stats;
    }

    /**
     * Result of checking all budget levels.
     */
    public record BudgetCheckResult(
        BudgetStatus sessionStatus,
        UserBudgetStatus userStatus,
        GlobalBudgetStatus globalStatus
    ) {}
}
