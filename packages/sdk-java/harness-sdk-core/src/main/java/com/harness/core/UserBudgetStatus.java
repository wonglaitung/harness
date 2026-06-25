package com.harness.core;

import com.harness.types.CostConfig;

/**
 * User-level budget status.
 */
public class UserBudgetStatus {

    private final boolean isWithinBudget;
    private final UserUsage usage;
    private final CostConfig config;
    private final String warningMessage;
    private final double usageRatio;

    public UserBudgetStatus(boolean isWithinBudget, UserUsage usage, CostConfig config,
                            String warningMessage, double usageRatio) {
        this.isWithinBudget = isWithinBudget;
        this.usage = usage;
        this.config = config;
        this.warningMessage = warningMessage;
        this.usageRatio = usageRatio;
    }

    public boolean isWithinBudget() {
        return isWithinBudget;
    }

    public UserUsage getUsage() {
        return usage;
    }

    public CostConfig getConfig() {
        return config;
    }

    public String getWarningMessage() {
        return warningMessage;
    }

    public double getUsageRatio() {
        return usageRatio;
    }
}
