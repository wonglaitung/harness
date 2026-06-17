package com.harness.core;

/**
 * Validation result for tool arguments.
 */
public record ValidationResult(
    boolean valid,
    String error
) {

    public static ValidationResult valid() {
        return new ValidationResult(true, null);
    }

    public static ValidationResult invalid(String error) {
        return new ValidationResult(false, error);
    }
}