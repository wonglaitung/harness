package com.harness.core;

/**
 * Global budget status.
 */
public class GlobalBudgetStatus {

    private final boolean isWithinBudget;
    private final double currentCost;
    private final double budget;
    private final String warningMessage;
    private final boolean shouldThrottle;

    public GlobalBudgetStatus(boolean isWithinBudget, double currentCost, double budget,
                              String warningMessage, boolean shouldThrottle) {
        this.isWithinBudget = isWithinBudget;
        this.currentCost = currentCost;
        this.budget = budget;
        this.warningMessage = warningMessage;
        this.shouldThrottle = shouldThrottle;
    }

    public boolean isWithinBudget() {
        return isWithinBudget;
    }

    public double getCurrentCost() {
        return currentCost;
    }

    public double getBudget() {
        return budget;
    }

    public String getWarningMessage() {
        return warningMessage;
    }

    public boolean shouldThrottle() {
        return shouldThrottle;
    }
}
