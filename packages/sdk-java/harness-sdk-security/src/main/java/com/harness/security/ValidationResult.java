package com.harness.security;

import java.util.List;

/**
 * Result of input validation.
 *
 * Contains validity status, errors, warnings, and sanitized text.
 */
public record ValidationResult(
    boolean valid,
    List<String> errors,
    List<String> warnings,
    String sanitizedText
) {

    /**
     * Create a valid result.
     */
    public static ValidationResult valid(String sanitizedText) {
        return new ValidationResult(true, List.of(), List.of(), sanitizedText);
    }

    /**
     * Create an invalid result with errors.
     */
    public static ValidationResult invalid(List<String> errors, String sanitizedText) {
        return new ValidationResult(false, errors, List.of(), sanitizedText);
    }

    /**
     * Create a result with warnings.
     */
    public static ValidationResult withWarnings(List<String> warnings, String sanitizedText) {
        return new ValidationResult(true, List.of(), warnings, sanitizedText);
    }

    /**
     * Check if input is completely safe (no errors or warnings).
     */
    public boolean isSafe() {
        return valid && warnings.isEmpty();
    }
}