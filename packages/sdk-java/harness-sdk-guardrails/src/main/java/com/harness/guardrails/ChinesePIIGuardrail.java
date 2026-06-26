package com.harness.guardrails;

import java.util.*;
import java.util.stream.Collectors;

/**
 * Chinese PII Guardrail.
 *
 * Comprehensive PII detection and redaction for Chinese text.
 * Supports both Simplified and Traditional Chinese.
 *
 * Example:
 * <pre>
 * ChinesePIIGuardrail guardrail = new ChinesePIIGuardrail();
 *
 * // Detect PII
 * List&lt;PIIEntity&gt; entities = guardrail.detect("我的手机号是13812345678");
 *
 * // Redact PII
 * String safeText = guardrail.redact("我的身份证号是110101199001011234");
 * // Output: "我的身份证号是<身份证号>"
 *
 * // Full check (detect + redact)
 * GuardrailResult result = guardrail.check("联系人：张三，电话：13912345678");
 * </pre>
 */
public class ChinesePIIGuardrail {

    // Default placeholders (Simplified Chinese)
    private static final Map<PIIEntity.Type, String> SIMPLIFIED_PLACEHOLDERS = Map.of(
        PIIEntity.Type.PHONE, "<手机号>",
        PIIEntity.Type.ID_CARD, "<身份证号>",
        PIIEntity.Type.BANK_CARD, "<银行卡号>",
        PIIEntity.Type.PASSPORT, "<护照号>",
        PIIEntity.Type.SOCIAL_CREDIT, "<统一社会信用代码>",
        PIIEntity.Type.LICENSE_PLATE, "<车牌号>",
        PIIEntity.Type.EMAIL, "<邮箱>",
        PIIEntity.Type.NAME, "<姓名>",
        PIIEntity.Type.IP_ADDRESS, "<IP地址>"
    );

    // Traditional Chinese placeholders
    private static final Map<PIIEntity.Type, String> TRADITIONAL_PLACEHOLDERS = Map.of(
        PIIEntity.Type.PHONE, "<手機號>",
        PIIEntity.Type.ID_CARD, "<身分證字號>",
        PIIEntity.Type.BANK_CARD, "<銀行卡號>",
        PIIEntity.Type.PASSPORT, "<護照號>",
        PIIEntity.Type.SOCIAL_CREDIT, "<統一社會信用代碼>",
        PIIEntity.Type.LICENSE_PLATE, "<車牌號>",
        PIIEntity.Type.EMAIL, "<信箱>",
        PIIEntity.Type.NAME, "<姓名>",
        PIIEntity.Type.IP_ADDRESS, "<IP位址>"
    );

    // English placeholders
    private static final Map<PIIEntity.Type, String> ENGLISH_PLACEHOLDERS = Map.of(
        PIIEntity.Type.PHONE, "<PHONE>",
        PIIEntity.Type.ID_CARD, "<ID_NUMBER>",
        PIIEntity.Type.BANK_CARD, "<BANK_CARD>",
        PIIEntity.Type.PASSPORT, "<PASSPORT>",
        PIIEntity.Type.SOCIAL_CREDIT, "<BUSINESS_ID>",
        PIIEntity.Type.LICENSE_PLATE, "<LICENSE_PLATE>",
        PIIEntity.Type.EMAIL, "<EMAIL>",
        PIIEntity.Type.NAME, "<NAME>",
        PIIEntity.Type.IP_ADDRESS, "<IP_ADDRESS>"
    );

    private final double minScore;
    private final ScriptType scriptType;
    private final boolean enableNameRecognition;
    private final Map<PIIEntity.Type, String> placeholders;

    // Recognizers
    private final ChinesePIIRecognizers.ChinaMobilePhoneRecognizer phoneRecognizer;
    private final ChinesePIIRecognizers.ChinaIDCardRecognizer idCardRecognizer;
    private final ChinesePIIRecognizers.ChinaBankCardRecognizer bankCardRecognizer;
    private final ChinesePIIRecognizers.ChinaPassportRecognizer passportRecognizer;
    private final ChinesePIIRecognizers.ChinaSocialCreditCodeRecognizer socialCreditRecognizer;
    private final ChinesePIIRecognizers.ChinaLicensePlateRecognizer licensePlateRecognizer;
    private final ChinesePIIRecognizers.HongKongPhoneRecognizer hkPhoneRecognizer;
    private final ChinesePIIRecognizers.HongKongIDCardRecognizer hkIdCardRecognizer;
    private final ChineseNameRecognizer nameRecognizer;

    /**
     * Script type for Chinese text.
     */
    public enum ScriptType {
        SIMPLIFIED,
        TRADITIONAL,
        ENGLISH,
        AUTO
    }

    /**
     * Guardrail result.
     */
    public static class GuardrailResult {
        public final String redactedText;
        public final List<PIIEntity> entities;
        public final boolean hasPII;

        public GuardrailResult(String redactedText, List<PIIEntity> entities, boolean hasPII) {
            this.redactedText = redactedText;
            this.entities = entities;
            this.hasPII = hasPII;
        }
    }

    /**
     * Create a Chinese PII Guardrail with default settings.
     */
    public ChinesePIIGuardrail() {
        this(0.5, ScriptType.AUTO, true);
    }

    /**
     * Create a Chinese PII Guardrail.
     *
     * @param minScore Minimum confidence threshold
     * @param scriptType Script type (SIMPLIFIED, TRADITIONAL, ENGLISH, AUTO)
     * @param enableNameRecognition Enable Chinese name recognition
     */
    public ChinesePIIGuardrail(double minScore, ScriptType scriptType, boolean enableNameRecognition) {
        this.minScore = minScore;
        this.scriptType = scriptType;
        this.enableNameRecognition = enableNameRecognition;
        this.placeholders = SIMPLIFIED_PLACEHOLDERS;

        // Initialize recognizers
        this.phoneRecognizer = new ChinesePIIRecognizers.ChinaMobilePhoneRecognizer();
        this.idCardRecognizer = new ChinesePIIRecognizers.ChinaIDCardRecognizer();
        this.bankCardRecognizer = new ChinesePIIRecognizers.ChinaBankCardRecognizer();
        this.passportRecognizer = new ChinesePIIRecognizers.ChinaPassportRecognizer();
        this.socialCreditRecognizer = new ChinesePIIRecognizers.ChinaSocialCreditCodeRecognizer();
        this.licensePlateRecognizer = new ChinesePIIRecognizers.ChinaLicensePlateRecognizer();
        this.hkPhoneRecognizer = new ChinesePIIRecognizers.HongKongPhoneRecognizer();
        this.hkIdCardRecognizer = new ChinesePIIRecognizers.HongKongIDCardRecognizer();
        this.nameRecognizer = enableNameRecognition ? new ChineseNameRecognizer(minScore) : null;
    }

    /**
     * Detect PII entities in text.
     *
     * @param text Text to analyze
     * @return List of detected PII entities
     */
    public List<PIIEntity> detect(String text) {
        List<PIIEntity> entities = new ArrayList<>();

        // Run all recognizers
        entities.addAll(phoneRecognizer.detect(text));
        entities.addAll(idCardRecognizer.detect(text));
        entities.addAll(bankCardRecognizer.detect(text));
        entities.addAll(passportRecognizer.detect(text));
        entities.addAll(socialCreditRecognizer.detect(text));
        entities.addAll(licensePlateRecognizer.detect(text));
        entities.addAll(hkPhoneRecognizer.detect(text));
        entities.addAll(hkIdCardRecognizer.detect(text));

        // Name recognition
        if (enableNameRecognition && nameRecognizer != null) {
            entities.addAll(nameRecognizer.detect(text));
        }

        // Filter by score
        entities = entities.stream()
            .filter(e -> e.getConfidence() >= minScore)
            .collect(Collectors.toList());

        // Deduplicate
        return deduplicateEntities(entities);
    }

    /**
     * Redact PII in text.
     *
     * @param text Text to redact
     * @return Redacted text
     */
    public String redact(String text) {
        List<PIIEntity> entities = detect(text);
        return redactWithPlaceholders(text, entities);
    }

    /**
     * Full check: detect and redact.
     *
     * @param text Text to check
     * @return Guardrail result with redacted text, entities, and PII flag
     */
    public GuardrailResult check(String text) {
        List<PIIEntity> entities = detect(text);
        boolean hasPII = !entities.isEmpty();

        String redactedText = hasPII ? redactWithPlaceholders(text, entities) : text;

        return new GuardrailResult(redactedText, entities, hasPII);
    }

    /**
     * Validate if text contains PII.
     *
     * @param text Text to validate
     * @return true if text is safe (no PII), false if contains PII
     */
    public boolean validate(String text) {
        return detect(text).isEmpty();
    }

    /**
     * Redact text with type placeholders.
     */
    private String redactWithPlaceholders(String text, List<PIIEntity> entities) {
        if (entities.isEmpty()) {
            return text;
        }

        // Detect script type
        ScriptType effectiveScriptType = scriptType;
        if (scriptType == ScriptType.AUTO) {
            effectiveScriptType = detectScript(text);
        }

        // Get appropriate placeholders
        Map<PIIEntity.Type, String> activePlaceholders = getPlaceholders(effectiveScriptType);

        // Sort by start position (descending) to replace from end
        List<PIIEntity> sorted = entities.stream()
            .sorted((a, b) -> Integer.compare(b.getStart(), a.getStart()))
            .collect(Collectors.toList());

        StringBuilder result = new StringBuilder(text);
        for (PIIEntity entity : sorted) {
            String placeholder = activePlaceholders.getOrDefault(
                entity.getType(),
                "<" + entity.getType().name() + ">"
            );

            result.replace(entity.getStart(), entity.getEnd(), placeholder);
        }

        return result.toString();
    }

    /**
     * Detect script type from text.
     */
    private ScriptType detectScript(String text) {
        // Traditional Chinese specific characters
        Set<Character> traditionalChars = Set.of(
            '們', '個', '時', '說', '國', '過', '這', '裡', '學', '經',
            '動', '點', '話', '書', '電', '車', '頭', '長', '問', '體',
            '機', '開', '樣', '東', '聽', '聲', '請', '義', '見', '間',
            '實', '氣', '報', '給', '起', '錢', '邊', '變', '還', '職',
            '傳', '優', '確', '調', '師', '產', '號', '場', '歷', '備'
        );

        // Simplified Chinese specific characters
        Set<Character> simplifiedChars = Set.of(
            '们', '个', '时', '说', '国', '过', '这', '里', '学', '经',
            '动', '点', '话', '书', '电', '车', '头', '长', '问', '体',
            '机', '开', '样', '东', '听', '声', '请', '义', '见', '间',
            '实', '气', '报', '给', '起', '钱', '边', '变', '还', '职',
            '传', '优', '确', '调', '师', '产', '号', '场', '历', '备'
        );

        int tcCount = 0;
        int scCount = 0;
        int cnCount = 0;
        int enCount = 0;

        for (char c : text.toCharArray()) {
            if (c >= '\u4e00' && c <= '\u9fff') {
                cnCount++;
                if (traditionalChars.contains(c)) {
                    tcCount++;
                } else if (simplifiedChars.contains(c)) {
                    scCount++;
                }
            } else if ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z')) {
                enCount++;
            }
        }

        // No Chinese characters = English
        if (cnCount == 0) {
            return ScriptType.ENGLISH;
        }

        // Determine by character count
        if (tcCount > scCount) {
            return ScriptType.TRADITIONAL;
        } else if (scCount > tcCount) {
            return ScriptType.SIMPLIFIED;
        }

        // Check for traditional keywords
        String[] traditionalKeywords = {
            "手機", "電話", "聯絡", "信箱", "身分證", "身份證", "護照", "銀行卡", "車牌"
        };
        for (String kw : traditionalKeywords) {
            if (text.contains(kw)) {
                return ScriptType.TRADITIONAL;
            }
        }

        return ScriptType.SIMPLIFIED;
    }

    /**
     * Get placeholders for script type.
     */
    private Map<PIIEntity.Type, String> getPlaceholders(ScriptType type) {
        switch (type) {
            case TRADITIONAL:
                return TRADITIONAL_PLACEHOLDERS;
            case ENGLISH:
                return ENGLISH_PLACEHOLDERS;
            default:
                return SIMPLIFIED_PLACEHOLDERS;
        }
    }

    /**
     * Remove duplicate/overlapping entities.
     */
    private List<PIIEntity> deduplicateEntities(List<PIIEntity> entities) {
        if (entities.isEmpty()) {
            return entities;
        }

        // Sort by start position, higher score first
        List<PIIEntity> sorted = entities.stream()
            .sorted((a, b) -> {
                int cmp = Integer.compare(a.getStart(), b.getStart());
                if (cmp == 0) {
                    return Double.compare(b.getConfidence(), a.getConfidence());
                }
                return cmp;
            })
            .collect(Collectors.toList());

        // Remove overlapping entities
        List<PIIEntity> result = new ArrayList<>();
        for (PIIEntity entity : sorted) {
            boolean overlaps = false;
            for (PIIEntity existing : result) {
                if (entity.getStart() < existing.getEnd() && entity.getEnd() > existing.getStart()) {
                    overlaps = true;
                    break;
                }
            }
            if (!overlaps) {
                result.add(entity);
            }
        }

        return result;
    }
}
