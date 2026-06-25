package com.harness.core;

/**
 * Budget status levels.
 *
 * - NORMAL: Within safe limits
 * - WARNING: Approaching limits (warning_threshold)
 * - CRITICAL: Near limits (critical_threshold)
 * - EXCEEDED: Budget exceeded, action required
 */
public enum BudgetLevel {
    NORMAL,
    WARNING,
    CRITICAL,
    EXCEEDED
}
