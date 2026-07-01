package com.harness.loop.types;

/**
 * Status of goal execution.
 *
 * <p>Represents the final state of a goal-driven execution.</p>
 *
 * <h2>States</h2>
 * <ul>
 *   <li>{@link #ACHIEVED} - Goal has been successfully achieved</li>
 *   <li>{@link #TIMEOUT} - Execution exceeded timeout limit</li>
 *   <li>{@link #MAX_ITERATIONS} - Maximum iterations reached</li>
 *   <li>{@link #MAX_RESETS} - Maximum context resets reached</li>
 *   <li>{@link #ERROR} - Agent execution error</li>
 *   <li>{@link #VERIFIER_FAULT} - Verifier failed (API rate limit, JSON parse error, etc.)</li>
 *   <li>{@link #CANCELLED} - User cancelled execution</li>
 * </ul>
 */
public enum GoalStatus {
    /**
     * Goal has been successfully achieved.
     */
    ACHIEVED("achieved"),

    /**
     * Execution exceeded timeout limit.
     */
    TIMEOUT("timeout"),

    /**
     * Maximum iterations reached without achieving the goal.
     */
    MAX_ITERATIONS("max_iterations"),

    /**
     * Maximum context resets reached.
     */
    MAX_RESETS("max_resets"),

    /**
     * Agent execution error occurred.
     */
    ERROR("error"),

    /**
     * Verifier failed (API rate limit, JSON parse error, etc.).
     */
    VERIFIER_FAULT("verifier_fault"),

    /**
     * User cancelled execution.
     */
    CANCELLED("cancelled");

    private final String value;

    GoalStatus(String value) {
        this.value = value;
    }

    /**
     * Get the string value of the status.
     *
     * @return String representation
     */
    public String getValue() {
        return value;
    }

    /**
     * Check if this is a terminal state (execution stopped).
     *
     * @return true if execution stopped without achieving the goal
     */
    public boolean isTerminal() {
        return this != ACHIEVED;
    }

    /**
     * Check if this represents successful completion.
     *
     * @return true if the goal was achieved
     */
    public boolean isSuccess() {
        return this == ACHIEVED;
    }

    /**
     * Parse from string value.
     *
     * @param value String value to parse
     * @return GoalStatus or null if not found
     */
    public static GoalStatus fromValue(String value) {
        for (GoalStatus status : values()) {
            if (status.value.equals(value)) {
                return status;
            }
        }
        return null;
    }
}
