package com.harness.core;

import com.harness.types.CostConfig;
import com.harness.types.TokenUsage;

/**
 * Current budget status.
 */
public class BudgetStatus {

    private final boolean isWithinBudget;
    private final TokenUsage usage;
    private final CostConfig config;
    private final String warningMessage;
    private final boolean shouldCompress;
    private final boolean shouldDowngrade;
    private final double usageRatio;

    public BudgetStatus(boolean isWithinBudget, TokenUsage usage, CostConfig config,
                        String warningMessage, boolean shouldCompress, boolean shouldDowngrade, double usageRatio) {
        this.isWithinBudget = isWithinBudget;
        this.usage = usage;
        this.config = config;
        this.warningMessage = warningMessage;
        this.shouldCompress = shouldCompress;
        this.shouldDowngrade = shouldDowngrade;
        this.usageRatio = usageRatio;
    }

    public boolean isWithinBudget() {
        return isWithinBudget;
    }

    public boolean isWarning() {
        return warningMessage != null && isWithinBudget;
    }

    public TokenUsage getUsage() {
        return usage;
    }

    public CostConfig getConfig() {
        return config;
    }

    public String getWarningMessage() {
        return warningMessage;
    }

    public boolean shouldCompress() {
        return shouldCompress;
    }

    public boolean shouldDowngrade() {
        return shouldDowngrade;
    }

    public double getUsageRatio() {
        return usageRatio;
    }

    public int getRemainingTokens() {
        return Math.max(0, config.maxTokensPerSession() - usage.totalTokens());
    }

    public int getRemainingToolCalls() {
        return Math.max(0, config.maxToolCallsPerSession() - usage.toolCalls());
    }
}
