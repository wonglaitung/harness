package com.harness.security;

import java.util.ArrayList;
import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Input validator.
 *
 * Validates input length and checks for injection patterns.
 */
public class InputValidator {

    private static final Logger logger = LoggerFactory.getLogger(InputValidator.class);

    /**
     * Default maximum input length.
     */
    public static final int DEFAULT_MAX_LENGTH = 100_000;

    private final int maxLength;
    private final PromptInjectionDetector injectionDetector;

    /**
     * Create validator with default settings.
     */
    public InputValidator() {
        this(DEFAULT_MAX_LENGTH, true, null);
    }

    /**
     * Create validator with custom settings.
     *
     * @param maxLength maximum input length
     * @param checkInjection whether to check for injection patterns
     * @param customPatterns custom injection patterns
     */
    public InputValidator(int maxLength, boolean checkInjection, List<String> customPatterns) {
        this.maxLength = maxLength;
        this.injectionDetector = checkInjection
            ? new PromptInjectionDetector(customPatterns)
            : null;
    }

    /**
     * Validate input.
     *
     * @param text input to validate
     * @return ValidationResult
     */
    public ValidationResult validate(String text) {
        List<String> errors = new ArrayList<>();
        List<String> warnings = new ArrayList<>();

        // Length check
        if (text.length() > maxLength) {
            errors.add("Input exceeds maximum length (" + maxLength + ")");
        }

        // Injection detection
        if (injectionDetector != null) {
            PromptInjectionDetector.DetectionResult detection = injectionDetector.detect(text);
            if (!detection.isSafe()) {
                warnings.add("Potential injection patterns detected: " + detection.detectedPatterns());
            }
        }

        // Sanitize text
        String sanitized = injectionDetector != null
            ? injectionDetector.sanitize(text)
            : text;

        if (!errors.isEmpty()) {
            logger.warn("Input validation failed: {}", errors);
            return ValidationResult.invalid(errors, sanitized);
        }

        if (!warnings.isEmpty()) {
            logger.warn("Input validation warnings: {}", warnings);
            return ValidationResult.withWarnings(warnings, sanitized);
        }

        return ValidationResult.valid(sanitized);
    }

    /**
     * Quick check if input is safe.
     *
     * @param text input to check
     * @return true if input passes all checks
     */
    public boolean isSafe(String text) {
        ValidationResult result = validate(text);
        return result.isSafe();
    }
}