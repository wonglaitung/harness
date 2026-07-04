package com.harness.security;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Input validator.
 *
 * Validates input length and checks for injection patterns.
 * Supports both plain text and multimodal content (list of content blocks).
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
     * @param text input to validate (String or multimodal content List)
     * @return ValidationResult
     */
    public ValidationResult validate(Object text) {
        List<String> errors = new ArrayList<>();
        List<String> warnings = new ArrayList<>();

        // Extract text content for length check
        String textContent = extractTextContent(text);

        // Length check
        if (textContent != null && textContent.length() > maxLength) {
            errors.add("Input exceeds maximum length (" + maxLength + ")");
        }

        // Injection detection
        if (injectionDetector != null && text != null) {
            PromptInjectionDetector.DetectionResult detection = injectionDetector.detect(text);
            if (!detection.isSafe()) {
                warnings.add("Potential injection patterns detected: " + detection.detectedPatterns());
            }
        }

        // Sanitize text
        Object sanitized = injectionDetector != null
            ? injectionDetector.sanitize(text)
            : text;

        // For ValidationResult, convert to string representation if multimodal
        String sanitizedText = sanitized instanceof String
            ? (String) sanitized
            : sanitized != null ? sanitized.toString() : "";

        if (!errors.isEmpty()) {
            logger.warn("Input validation failed: {}", errors);
            return ValidationResult.invalid(errors, sanitizedText);
        }

        if (!warnings.isEmpty()) {
            logger.warn("Input validation warnings: {}", warnings);
            return ValidationResult.withWarnings(warnings, sanitizedText);
        }

        return ValidationResult.valid(sanitizedText);
    }

    /**
     * Quick check if input is safe.
     *
     * @param text input to check (String or multimodal content List)
     * @return true if input passes all checks
     */
    public boolean isSafe(Object text) {
        ValidationResult result = validate(text);
        return result.isSafe();
    }

    /**
     * Extract text content from input.
     * Handles both String and multimodal content (List of Maps).
     *
     * @param input String or multimodal content List
     * @return extracted text content, or null if no text found
     */
    @SuppressWarnings("unchecked")
    private String extractTextContent(Object input) {
        if (input instanceof String) {
            return (String) input;
        }

        if (input instanceof List) {
            StringBuilder textBuilder = new StringBuilder();
            for (Object block : (List<?>) input) {
                if (block instanceof Map) {
                    Map<String, Object> blockMap = (Map<String, Object>) block;
                    if ("text".equals(blockMap.get("type"))) {
                        Object textObj = blockMap.get("text");
                        if (textObj instanceof String) {
                            textBuilder.append((String) textObj);
                        }
                    }
                }
            }
            return textBuilder.length() > 0 ? textBuilder.toString() : null;
        }

        return null;
    }
}