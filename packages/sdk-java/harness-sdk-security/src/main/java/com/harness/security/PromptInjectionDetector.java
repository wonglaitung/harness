package com.harness.security;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * Prompt injection detector.
 *
 * Detects common injection patterns in user input.
 * Supports both plain text and multimodal content (list of content blocks).
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
     * @param text text to analyze (String or multimodal content List)
     * @return DetectionResult with safety status and detected patterns
     */
    public DetectionResult detect(Object text) {
        String textContent = extractTextContent(text);

        if (textContent == null || textContent.isEmpty()) {
            return new DetectionResult(true, List.of());
        }

        List<String> detected = new ArrayList<>();

        for (Pattern pattern : patterns) {
            if (pattern.matcher(textContent).find()) {
                detected.add(pattern.pattern());
            }
        }

        return new DetectionResult(detected.isEmpty(), detected);
    }

    /**
     * Sanitize text by filtering detected patterns.
     *
     * @param text text to sanitize (String or multimodal content List)
     * @return sanitized content (same type as input)
     */
    public Object sanitize(Object text) {
        if (text instanceof String) {
            return sanitizeString((String) text);
        } else if (text instanceof List) {
            return sanitizeMultimodalContent((List<?>) text);
        }
        return text;
    }

    /**
     * Sanitize plain text string.
     */
    private String sanitizeString(String text) {
        String sanitized = text;
        for (Pattern pattern : patterns) {
            sanitized = pattern.matcher(sanitized).replaceAll("[FILTERED]");
        }
        return sanitized;
    }

    /**
     * Sanitize multimodal content list.
     * Only text blocks are sanitized; other blocks are preserved.
     */
    @SuppressWarnings("unchecked")
    private List<?> sanitizeMultimodalContent(List<?> content) {
        List<Object> sanitizedList = new ArrayList<>();

        for (Object block : content) {
            if (block instanceof Map) {
                Map<String, Object> blockMap = (Map<String, Object>) block;
                if ("text".equals(blockMap.get("type"))) {
                    // Sanitize text blocks
                    String text = (String) blockMap.get("text");
                    String sanitizedText = sanitizeString(text);
                    Map<String, Object> sanitizedBlock = new java.util.HashMap<>(blockMap);
                    sanitizedBlock.put("text", sanitizedText);
                    sanitizedList.add(sanitizedBlock);
                } else {
                    // Keep non-text blocks unchanged
                    sanitizedList.add(block);
                }
            } else {
                sanitizedList.add(block);
            }
        }

        return sanitizedList;
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
            return textBuilder.toString();
        }

        return null;
    }

    /**
     * Result of injection detection.
     */
    public record DetectionResult(boolean isSafe, List<String> detectedPatterns) {
    }
}