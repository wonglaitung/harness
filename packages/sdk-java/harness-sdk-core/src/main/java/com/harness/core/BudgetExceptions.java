package com.harness.core;

import com.harness.types.TokenUsage;

/**
 * Exceptions for budget control.
 *
 * Used when token or cost limits are exceeded at different levels:
 * - Session level: BudgetExceededException
 * - User level: UserBudgetExceededException
 * - Global level: GlobalBudgetExceededException
 */
public class BudgetExceptions {

    /**
     * Thrown when session budget is exceeded.
     */
    public static class BudgetExceededException extends RuntimeException {
        private final TokenUsage usage;
        private final int limit;

        public BudgetExceededException(String message) {
            super(message);
            this.usage = null;
            this.limit = 0;
        }

        public BudgetExceededException(String message, TokenUsage usage, int limit) {
            super(message);
            this.usage = usage;
            this.limit = limit;
        }

        public TokenUsage usage() { return usage; }
        public int limit() { return limit; }
    }

    /**
     * Thrown when user-level budget is exceeded.
     */
    public static class UserBudgetExceededException extends RuntimeException {
        private final String userId;
        private final int limit;

        public UserBudgetExceededException(String message) {
            super(message);
            this.userId = "";
            this.limit = 0;
        }

        public UserBudgetExceededException(String message, String userId, int limit) {
            super(message);
            this.userId = userId;
            this.limit = limit;
        }

        public String userId() { return userId; }
        public int limit() { return limit; }
    }

    /**
     * Thrown when global budget is exceeded.
     */
    public static class GlobalBudgetExceededException extends RuntimeException {
        private final double currentCost;
        private final double budget;

        public GlobalBudgetExceededException(String message) {
            super(message);
            this.currentCost = 0;
            this.budget = 0;
        }

        public GlobalBudgetExceededException(String message, double currentCost, double budget) {
            super(message);
            this.currentCost = currentCost;
            this.budget = budget;
        }

        public double currentCost() { return currentCost; }
        public double budget() { return budget; }
    }
}
