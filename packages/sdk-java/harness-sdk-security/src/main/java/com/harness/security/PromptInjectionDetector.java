package com.harness.security;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * Prompt injection detector.
 *
 * Detects common injection patterns in user input.
 */
public class PromptInjectionDetector {

    /**
     * Default injection patterns to detect.
     */
    public static final List<String> DEFAULT_INJECTION_PATTERNS = List.of(
        // Role playing
        "ignore (all )?(previous|above) instructions",
        "disregard (all )?(previous|above) instructions",
        "forget (all )?(previous|above) instructions",
        // System prompt leakage
        "what (is|are) your (system |initial )?instructions",
        "repeat your (system |initial )?prompt",
        "show me your (system |initial )?prompt",
        // Jailbreak attempts
        "you are now (a|an) \\w+",
        "pretend (to be|you are)",
        "act as (if|though)",
        // Encoding bypass
        "base64",
        "rot13",
        "hex encode",
        // Dangerous instructions
        "sudo",
        "chmod",
        "rm -rf",
        "delete all",
        "format disk",
        // Output manipulation
        "output your prompt",
        "print your instructions",
        "reveal your system"
    );

    private final List<Pattern> patterns;

    /**
     * Create detector with default patterns.
     */
    public PromptInjectionDetector() {
        this(null);
    }

    /**
     * Create detector with custom patterns.
     *
     * @param customPatterns additional patterns to detect
     */
    public PromptInjectionDetector(List<String> customPatterns) {
        this.patterns = new ArrayList<>();

        // Add default patterns
        for (String pattern : DEFAULT_INJECTION_PATTERNS) {
            this.patterns.add(Pattern.compile(pattern, Pattern.CASE_INSENSITIVE));
        }

        // Add custom patterns
        if (customPatterns != null) {
            for (String pattern : customPatterns) {
                this.patterns.add(Pattern.compile(pattern, Pattern.CASE_INSENSITIVE));
            }
        }
    }

    /**
     * Detect injection attempts.
     *
     * @param text text to analyze
     * @return DetectionResult with safety status and detected patterns
     */
    public DetectionResult detect(String text) {
        List<String> detected = new ArrayList<>();

        for (Pattern pattern : patterns) {
            if (pattern.matcher(text).find()) {
                detected.add(pattern.pattern());
            }
        }

        return new DetectionResult(detected.isEmpty(), detected);
    }

    /**
     * Sanitize text by filtering detected patterns.
     *
     * @param text text to sanitize
     * @return sanitized text
     */
    public String sanitize(String text) {
        String sanitized = text;

        for (Pattern pattern : patterns) {
            sanitized = pattern.matcher(sanitized).replaceAll("[FILTERED]");
        }

        return sanitized;
    }

    /**
     * Result of injection detection.
     */
    public record DetectionResult(boolean isSafe, List<String> detectedPatterns) {
    }
}