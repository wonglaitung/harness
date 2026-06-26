package com.harness.core;

/**
 * Validation result for tool arguments.
 */
public record ValidationResult(
    boolean isValid,
    String error
) {

    /**
     * Create a valid result.
     */
    public static ValidationResult valid() {
        return new ValidationResult(true, null);
    }

    /**
     * Create an invalid result.
     */
    public static ValidationResult invalid(String error) {
        return new ValidationResult(false, error);
    }

    /**
     * Check if validation passed (convenience method).
     */
    public boolean passed() {
        return isValid;
    }
}