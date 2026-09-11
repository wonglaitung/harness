package com.harness.security;

import java.text.Normalizer;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * Prompt injection detector (M6-B enhanced).
 *
 * Detects common injection patterns in user input.
 * Supports both plain text and multimodal content (list of content blocks).
 *
 * <p>M6 additions: NFKC normalization + confusable mapping to defeat
 * full-width/homoglyph bypass; optional {@link InjectionClassifier} for
 * semantic-level scoring (threshold &ge; 0.5 = injection).</p>
 */
public class PromptInjectionDetector {

    /**
     * Pluggable semantic injection classifier.
     * Implementations score text on [0,1]; &ge; 0.5 is treated as injection.
     * Exceptions thrown by the classifier are swallowed (must not break validation).
     */
    public interface InjectionClassifier {
        /**
         * Score the given (normalized) text for injection likelihood.
         *
         * @param text normalized input text
         * @return score in [0, 1]; &ge; 0.5 = injection
         */
        float classify(String text);
    }

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

    /** Confusable character mapping (Cyrillic/math/typographic → ASCII). */
    private static final Map<Character, Character> CONFUSABLES = Map.ofEntries(
        // Cyrillic
        Map.entry('а', 'a'), Map.entry('е', 'e'), Map.entry('о', 'o'),
        Map.entry('р', 'p'), Map.entry('с', 'c'), Map.entry('у', 'y'),
        Map.entry('х', 'x'), Map.entry('А', 'A'), Map.entry('В', 'B'),
        Map.entry('Е', 'E'), Map.entry('К', 'K'), Map.entry('М', 'M'),
        Map.entry('Н', 'H'), Map.entry('О', 'O'), Map.entry('Р', 'P'),
        Map.entry('С', 'C'), Map.entry('Т', 'T'), Map.entry('У', 'Y'),
        Map.entry('Х', 'X'),
        // Full-width ASCII
        Map.entry('ｉ', 'i'), Map.entry('ｇ', 'g'), Map.entry('ｎ', 'n'),
        Map.entry('ｏ', 'o'), Map.entry('ｒ', 'r'), Map.entry('ｅ', 'e'),
        // Common typographic
        Map.entry('—', '-'), Map.entry('–', '-'), Map.entry(''', '\''),
        Map.entry(''', '\''), Map.entry('"', '"'), Map.entry('"', '"'),
        Map.entry('…', '...')
    );

    private static final float CLASSIFIER_THRESHOLD = 0.5f;

    private final List<Pattern> patterns;
    private final InjectionClassifier classifier;

    /**
     * Create detector with default patterns, no classifier.
     */
    public PromptInjectionDetector() {
        this(null, null);
    }

    /**
     * Create detector with custom patterns.
     *
     * @param customPatterns additional patterns to detect (may be null)
     */
    public PromptInjectionDetector(List<String> customPatterns) {
        this(customPatterns, null);
    }

    /**
     * Create detector with custom patterns and a semantic classifier.
     *
     * @param customPatterns additional patterns to detect (may be null)
     * @param classifier     optional semantic classifier; exceptions are swallowed
     */
    public PromptInjectionDetector(List<String> customPatterns, InjectionClassifier classifier) {
        this.classifier = classifier;
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
     * <p>Processing order: extract text → normalize (NFKC + confusable mapping) →
     * regex pattern match → optional semantic classifier.  The classifier score is
     * reported in {@link DetectionResult#score()} but does <b>not</b> override the
     * regex-based {@code isSafe} flag; callers should use {@code score()} for
     * combined risk assessment.</p>
     *
     * @param text text to analyze (String or multimodal content List)
     * @return DetectionResult with safety status, detected patterns, and score
     */
    public DetectionResult detect(Object text) {
        String textContent = extractTextContent(text);

        if (textContent == null || textContent.isEmpty()) {
            return new DetectionResult(true, List.of(), 0.0f);
        }

        // Normalize: NFKC + confusable mapping
        String normalized = normalize(textContent);

        List<String> detected = new ArrayList<>();

        for (Pattern pattern : patterns) {
            if (pattern.matcher(normalized).find()) {
                detected.add(pattern.pattern());
            }
        }

        // Semantic classifier (exceptions swallowed)
        float score = 0.0f;
        if (classifier != null) {
            try {
                score = classifier.classify(normalized);
                if (score >= CLASSIFIER_THRESHOLD && detected.isEmpty()) {
                    detected.add("classifier:" + score);
                }
            } catch (Exception e) {
                // Classifier must not break validation
            }
        }

        return new DetectionResult(detected.isEmpty(), detected, score);
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
     * Normalize text: NFKC normalization + confusable character replacement.
     *
     * <p>Defeats full-width characters, homoglyph substitution, and
     * typographic character obfuscation.</p>
     *
     * @param text raw input text
     * @return normalized text with confusables mapped to ASCII
     */
    public static String normalize(String text) {
        if (text == null || text.isEmpty()) {
            return text;
        }

        // Step 1: NFKC normalization (full-width → half-width, compatibility decompose)
        String nfkc = Normalizer.normalize(text, Normalizer.Form.NFKC);

        // Step 2: Confusable character mapping
        StringBuilder sb = new StringBuilder(nfkc.length());
        for (int i = 0; i < nfkc.length(); i++) {
            char c = nfkc.charAt(i);
            sb.append(CONFUSABLES.getOrDefault(c, c));
        }

        // Step 3: Strip zero-width characters
        String result = sb.toString()
            .replace("\u200B", "")  // ZERO WIDTH SPACE
            .replace("\u200C", "")  // ZERO WIDTH NON-JOINER
            .replace("\u200D", "")  // ZERO WIDTH JOINER
            .replace("\uFEFF", ""); // BOM / ZERO WIDTH NO-BREAK SPACE

        return result;
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
     * Result of injection detection (M6-B: now includes score).
     *
     * @param isSafe           true if no patterns detected
     * @param detectedPatterns list of matched pattern strings
     * @param score            semantic classifier score [0,1]; 0 if no classifier
     */
    public record DetectionResult(boolean isSafe, List<String> detectedPatterns, float score) {
    }
}
