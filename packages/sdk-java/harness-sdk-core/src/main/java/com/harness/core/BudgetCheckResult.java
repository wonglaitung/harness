package com.harness.core;

/**
 * Result of a budget check.
 *
 * @param level Current budget level
 * @param isWithinBudget True if budget not exceeded
 * @param message Human-readable status message
 * @param remainingIterations Remaining iterations allowed
 * @param remainingToolCalls Remaining tool calls allowed
 * @param shouldStop True if execution should stop
 * @param throttleLimit Optional throttle limit for tool calls
 */
public record BudgetCheckResult(
    BudgetLevel level,
    boolean isWithinBudget,
    String message,
    int remainingIterations,
    int remainingToolCalls,
    boolean shouldStop,
    Integer throttleLimit
) {

    /**
     * Create a normal result.
     */
    public static BudgetCheckResult normal(String message) {
        return new BudgetCheckResult(BudgetLevel.NORMAL, true, message, 0, 0, false, null);
    }

    /**
     * Create an exceeded result.
     */
    public static BudgetCheckResult exceeded(String message, boolean shouldStop) {
        return new BudgetCheckResult(BudgetLevel.EXCEEDED, false, message, 0, 0, shouldStop, null);
    }
}
