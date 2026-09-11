package com.harness.security;

import java.text.Normalizer;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * Prompt injection detector (M6-B enhanced).
 *
 * Detects common injection patterns in user input (English + Chinese/multilingual).
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
     * Default injection patterns — English + Chinese/multilingual (M5-B coverage).
     */
    public static final List<String> DEFAULT_INJECTION_PATTERNS = List.of(
        // ---- Role playing (English) ----
        "ignore (all )?(previous|above) instructions",
        "disregard (all )?(previous|above) instructions",
        "forget (all )?(previous|above) instructions",
        // ---- System prompt leakage (English) ----
        "what (is|are) your (system |initial )?instructions",
        "repeat your (system |initial )?prompt",
        "show me your (system |initial )?prompt",
        // ---- Jailbreak attempts (English) ----
        "you are now (a|an) \\w+",
        "pretend (to be|you are)",
        "act as (if|though)",
        "developer mode",
        "\\bDAN\\b",
        // ---- Encoding bypass ----
        "base64",
        "rot13",
        "hex encode",
        "decode and (run|execute)",
        // ---- Dangerous instructions (English) ----
        "sudo",
        "chmod",
        "rm -rf",
        "delete all",
        "format disk",
        "output your prompt",
        "print your instructions",
        "reveal your system",
        // ---- Chinese / multilingual: 忽略/无视/忘掉指令 ----
        "忽略(以上|之前|前述|上面|先前|所有)?(的)?(所有)?(指令|指示|要求|提示|设定|限制|规则|约束|安全|prompt)",
        "无视(以上|之前|前述|上面|先前)?(的)?(指令|指示|要求|提示|设定|限制|规则|约束|安全)",
        "忘(记|掉)(以上|之前|前述|上面|先前)?(的)?(指令|指示|要求|提示|设定|限制|规则|约束)",
        "不要(理会|理睬|管|搭理)(以上|之前|前面|先前)?(的)?(指令|指示|要求|提示|限制|规则)",
        "把(上面|之前|以上)(的)?(指令|指示|要求|提示)(全部)?(抛|丢|扔)到(一|脑)边",
        // ---- Chinese: 系统提示泄露 ----
        "(告诉|展示|显示|透露|念出|重复|说出|拷贝)(我)?(你的)?(系统|初始|system)?(提示|指令|prompt)",
        "你的(系统|初始|system)?(提示|指令|prompt)(是(什么|啥)|内容|是什么)",
        "(输出|打印|显示)(你(的)?(系统|初始|system)?(提示|指令|prompt))",
        "(泄露|泄漏|透露)(你(的)?)(系统|初始|system)(提示|指令|prompt)",
        // ---- Chinese: 越狱 / 角色扮演 ----
        "假装(你|我)是",
        "假设(你|我)是",
        "扮演(一个|一名|一种|a|an|成)",
        "(现在|现在)你(就)?(是|变成).{0,10}(限制|约束|规则|安全)",
        "越(狱)",
        // ---- Chinese: 危险指令 ----
        "删除(所有|全部|一切)?(的)?(文件|数据|记录|资料)",
        "格式化(磁盘|硬盘|磁碟|系统)",
        "(运行|执行|执行)(以下|下列|这个|恶意)?(的)?(命令|指令|脚本)",
        "(解密|解码)(后|之后)(运行|执行)"
    );

    /** Zero-width / invisible characters stripped before matching. */
    private static final Pattern ZERO_WIDTH = Pattern.compile(
        "[\u200b\u200c\u200d\u2060\ufeff\u00ad]");

    /** Confusable character mapping (Cyrillic/math/typographic → ASCII). */
    private static final Map<Character, Character> CONFUSABLES = Map.ofEntries(
        // Cyrillic → Latin
        Map.entry('а', 'a'), Map.entry('е', 'e'), Map.entry('о', 'o'),
        Map.entry('р', 'p'), Map.entry('с', 'c'), Map.entry('у', 'y'),
        Map.entry('х', 'x'), Map.entry('і', 'i'), Map.entry('ј', 'j'),
        Map.entry('ѕ', 's'), Map.entry('ԛ', 'q'), Map.entry('ɡ', 'g'),
        Map.entry('ӏ', 'l'),
        Map.entry('А', 'A'), Map.entry('В', 'B'), Map.entry('Е', 'E'),
        Map.entry('К', 'K'), Map.entry('М', 'M'), Map.entry('Н', 'H'),
        Map.entry('О', 'O'), Map.entry('Р', 'P'), Map.entry('С', 'C'),
        Map.entry('Т', 'T'), Map.entry('Х', 'X'), Map.entry('І', 'I'),
        // Full-width ASCII
        Map.entry('ｉ', 'i'), Map.entry('ｇ', 'g'), Map.entry('ｎ', 'n'),
        Map.entry('ｏ', 'o'), Map.entry('ｒ', 'r'), Map.entry('ｅ', 'e'),
        // Common typographic
        Map.entry('\u2014', '-'), Map.entry('\u2013', '-'), Map.entry('\u2018', '\''),
        Map.entry('\u2019', '\''), Map.entry('\u201c', '"'), Map.entry('\u201d', '"'),
        Map.entry('\u2026', "...")
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
     * <p>Processing order: extract text → normalize (strip zero-width → NFKC → confusable) →
     * regex pattern match → optional semantic classifier.</p>
     *
     * @param text text to analyze (String or multimodal content List)
     * @return DetectionResult with safety status, detected patterns, and score
     */
    public DetectionResult detect(Object text) {
        String textContent = extractTextContent(text);

        if (textContent == null || textContent.isEmpty()) {
            return new DetectionResult(true, List.of(), 0.0f);
        }

        // Normalize: strip zero-width → NFKC → confusable mapping
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
                if (score >= CLASSIFIER_THRESHOLD) {
                    detected.add("semantic:" + String.format("%.2f", score));
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
     * <p>M6 fix: normalizes text before pattern replacement so confusable/
     * obfuscated patterns are caught in the output too.</p>
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
     * Normalize text: strip zero-width → NFKC → confusable mapping.
     *
     * <p>Defeats zero-width insertion, full-width characters, homoglyph
     * substitution, and typographic character obfuscation.</p>
     *
     * @param text raw input text
     * @return normalized text
     */
    public static String normalize(String text) {
        if (text == null || text.isEmpty()) {
            return text;
        }

        // Step 1: Strip zero-width / invisible characters
        String stripped = ZERO_WIDTH.matcher(text).replaceAll("");

        // Step 2: NFKC normalization (full-width → half-width, compatibility decompose)
        String nfkc = Normalizer.normalize(stripped, Normalizer.Form.NFKC);

        // Step 3: Confusable character mapping
        StringBuilder sb = new StringBuilder(nfkc.length());
        for (int i = 0; i < nfkc.length(); i++) {
            char c = nfkc.charAt(i);
            sb.append(CONFUSABLES.getOrDefault(c, c));
        }

        return sb.toString();
    }

    /**
     * Sanitize plain text string (normalizes first, then replaces patterns).
     */
    private String sanitizeString(String text) {
        String normalized = normalize(text);
        String sanitized = normalized;
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
                    String text = (String) blockMap.get("text");
                    String sanitizedText = sanitizeString(text);
                    Map<String, Object> sanitizedBlock = new java.util.HashMap<>(blockMap);
                    sanitizedBlock.put("text", sanitizedText);
                    sanitizedList.add(sanitizedBlock);
                } else {
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
     * Result of injection detection (M6-B: includes score).
     *
     * @param isSafe           true if no patterns detected
     * @param detectedPatterns list of matched pattern strings
     * @param score            semantic classifier score [0,1]; 0 if no classifier
     */
    public record DetectionResult(boolean isSafe, List<String> detectedPatterns, float score) {
    }
}
