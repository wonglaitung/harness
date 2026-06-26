package com.harness.guardrails;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Chinese PII Recognizers.
 *
 * Provides specialized PII detection for Chinese personal information:
 * - China mobile phone numbers
 * - China ID card numbers (18-digit and 15-digit)
 * - China bank card numbers
 * - China passport numbers
 * - China social credit codes
 * - China license plates
 * - Hong Kong phone numbers
 * - Hong Kong ID cards
 *
 * Supports both Simplified and Traditional Chinese context.
 */
public class ChinesePIIRecognizers {

    // =========================================================================
    // China Mobile Phone Recognizer
    // =========================================================================

    /**
     * Recognize Chinese mobile phone numbers.
     * Format: 1[3-9]xxxxxxxxx (11 digits starting with 1)
     */
    public static class ChinaMobilePhoneRecognizer {
        private static final Pattern PATTERN = Pattern.compile("(?<!\\d)(1[3-9]\\d{9})(?!\\d)");
        private static final double SCORE = 0.95;

        private static final Set<String> CONTEXT = Set.of(
            // Simplified Chinese
            "手机", "电话", "联系电话", "联系方式", "手机号", "移动电话", "电话号码", "联系手机",
            // Traditional Chinese
            "手機", "手機號", "手機號碼", "電話", "電話號碼", "聯絡電話", "聯絡方式", "行動電話",
            // English
            "mobile", "phone"
        );

        public List<PIIEntity> detect(String text) {
            List<PIIEntity> entities = new ArrayList<>();
            Matcher matcher = PATTERN.matcher(text);

            while (matcher.find()) {
                double finalScore = hasContext(text, matcher.start(), CONTEXT)
                    ? SCORE
                    : SCORE * 0.8;

                entities.add(new PIIEntity(
                    PIIEntity.Type.PHONE,
                    matcher.group(),
                    matcher.start(),
                    matcher.end(),
                    finalScore
                ));
            }

            return entities;
        }
    }

    // =========================================================================
    // China ID Card Recognizer
    // =========================================================================

    /**
     * Recognize Chinese ID card numbers.
     * 18-digit format: province code + birth date + sequence + checksum
     * 15-digit format: older style (legacy)
     */
    public static class ChinaIDCardRecognizer {
        // 18-digit ID card with valid date
        private static final Pattern PATTERN_18 = Pattern.compile(
            "(?<!\\d)([1-9]\\d{5}(?:19|20)\\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\\d|3[01])\\d{3}[\\dXx])(?!\\d)"
        );
        // 15-digit ID card (legacy)
        private static final Pattern PATTERN_15 = Pattern.compile(
            "(?<!\\d)([1-9]\\d{5}\\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\\d|3[01])\\d{3})(?!\\d)"
        );
        private static final double SCORE_18 = 0.95;
        private static final double SCORE_15 = 0.85;

        private static final Set<String> CONTEXT = Set.of(
            // Simplified Chinese
            "身份证", "身份证号", "证件号", "身份号码", "身份证号码", "证件号码", "公民身份号码",
            // Traditional Chinese
            "身分證", "身分證字號", "身分證號碼", "證件號", "證件號碼", "身份證", "身份證號",
            // English
            "ID", "ID number"
        );

        public List<PIIEntity> detect(String text) {
            List<PIIEntity> entities = new ArrayList<>();

            // Check 18-digit format
            Matcher matcher18 = PATTERN_18.matcher(text);
            while (matcher18.find()) {
                double finalScore = hasContext(text, matcher18.start(), CONTEXT)
                    ? SCORE_18
                    : SCORE_18 * 0.8;

                entities.add(new PIIEntity(
                    PIIEntity.Type.ID_CARD,
                    matcher18.group(),
                    matcher18.start(),
                    matcher18.end(),
                    finalScore
                ));
            }

            // Check 15-digit format
            Matcher matcher15 = PATTERN_15.matcher(text);
            while (matcher15.find()) {
                double finalScore = hasContext(text, matcher15.start(), CONTEXT)
                    ? SCORE_15
                    : SCORE_15 * 0.8;

                entities.add(new PIIEntity(
                    PIIEntity.Type.ID_CARD,
                    matcher15.group(),
                    matcher15.start(),
                    matcher15.end(),
                    finalScore
                ));
            }

            return entities;
        }
    }

    // =========================================================================
    // China Bank Card Recognizer
    // =========================================================================

    /**
     * Recognize Chinese bank card numbers.
     * Format: 16-19 digits
     */
    public static class ChinaBankCardRecognizer {
        private static final Pattern PATTERN = Pattern.compile("(?<!\\d)(\\d{16,19})(?!\\d)");
        private static final double SCORE = 0.6;

        private static final Set<String> CONTEXT = Set.of(
            // Simplified Chinese
            "银行卡", "银行卡号", "卡号", "账号", "账户", "储蓄卡", "信用卡", "借记卡",
            // Traditional Chinese
            "銀行卡", "銀行卡號", "銀行帳號", "卡號", "帳號", "帳戶", "儲蓄卡", "信用卡", "借記卡",
            // English
            "card", "bank card", "account"
        );

        public List<PIIEntity> detect(String text) {
            List<PIIEntity> entities = new ArrayList<>();
            Matcher matcher = PATTERN.matcher(text);

            while (matcher.find()) {
                // Bank card has low base score, context significantly improves it
                double finalScore = hasContext(text, matcher.start(), CONTEXT)
                    ? SCORE + 0.25
                    : SCORE;

                entities.add(new PIIEntity(
                    PIIEntity.Type.BANK_CARD,
                    matcher.group(),
                    matcher.start(),
                    matcher.end(),
                    finalScore
                ));
            }

            return entities;
        }
    }

    // =========================================================================
    // China Passport Recognizer
    // =========================================================================

    /**
     * Recognize Chinese passport numbers.
     * Format: E/G + 8 digits
     */
    public static class ChinaPassportRecognizer {
        private static final Pattern PATTERN = Pattern.compile("(?<![A-Za-z0-9])([EG]\\d{8})(?![A-Za-z0-9])", Pattern.CASE_INSENSITIVE);
        private static final double SCORE = 0.9;

        private static final Set<String> CONTEXT = Set.of(
            // Simplified Chinese
            "护照", "护照号", "护照号码",
            // Traditional Chinese
            "護照", "護照號", "護照號碼",
            // English
            "passport"
        );

        public List<PIIEntity> detect(String text) {
            List<PIIEntity> entities = new ArrayList<>();
            Matcher matcher = PATTERN.matcher(text);

            while (matcher.find()) {
                double finalScore = hasContext(text, matcher.start(), CONTEXT)
                    ? SCORE
                    : SCORE * 0.8;

                entities.add(new PIIEntity(
                    PIIEntity.Type.PASSPORT,
                    matcher.group(),
                    matcher.start(),
                    matcher.end(),
                    finalScore
                ));
            }

            return entities;
        }
    }

    // =========================================================================
    // China Social Credit Code Recognizer
    // =========================================================================

    /**
     * Recognize China Unified Social Credit Codes.
     * Format: 18 characters (letters and digits, excluding I, O, Z, S, V)
     */
    public static class ChinaSocialCreditCodeRecognizer {
        private static final Pattern PATTERN = Pattern.compile(
            "(?<![A-Za-z0-9])([0-9A-HJ-NPQRTUWXY]{2}\\d{6}[0-9A-HJ-NPQRTUWXY]{10})(?![A-Za-z0-9])"
        );
        private static final double SCORE = 0.9;

        private static final Set<String> CONTEXT = Set.of(
            // Simplified Chinese
            "统一社会信用代码", "社会信用代码", "信用代码", "企业代码", "营业执照号",
            // Traditional Chinese
            "統一社會信用代碼", "社會信用代碼", "信用代碼", "企業代碼", "營業執照號"
        );

        public List<PIIEntity> detect(String text) {
            List<PIIEntity> entities = new ArrayList<>();
            Matcher matcher = PATTERN.matcher(text);

            while (matcher.find()) {
                double finalScore = hasContext(text, matcher.start(), CONTEXT)
                    ? SCORE
                    : SCORE * 0.8;

                entities.add(new PIIEntity(
                    PIIEntity.Type.SOCIAL_CREDIT,
                    matcher.group(),
                    matcher.start(),
                    matcher.end(),
                    finalScore
                ));
            }

            return entities;
        }
    }

    // =========================================================================
    // China License Plate Recognizer
    // =========================================================================

    /**
     * Recognize Chinese vehicle license plates.
     * Format: province abbreviation + letter + 5-6 alphanumeric characters
     */
    public static class ChinaLicensePlateRecognizer {
        private static final String PROVINCES = "京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼";
        private static final Pattern PATTERN = Pattern.compile(
            "(?<![" + PROVINCES + "A-Z])([" + PROVINCES + "使领][A-Z][A-HJ-NP-Z0-9]{4,5}[A-HJ-NP-Z0-9学警港澳])(?![A-HJ-NP-Z0-9])"
        );
        private static final double SCORE = 0.9;

        private static final Set<String> CONTEXT = Set.of(
            // Simplified Chinese
            "车牌", "车牌号", "车牌号码", "车辆号牌",
            // Traditional Chinese
            "車牌", "車牌號", "車牌號碼", "車輛號牌",
            // English
            "license plate", "plate"
        );

        public List<PIIEntity> detect(String text) {
            List<PIIEntity> entities = new ArrayList<>();
            Matcher matcher = PATTERN.matcher(text);

            while (matcher.find()) {
                double finalScore = hasContext(text, matcher.start(), CONTEXT)
                    ? SCORE
                    : SCORE * 0.8;

                entities.add(new PIIEntity(
                    PIIEntity.Type.LICENSE_PLATE,
                    matcher.group(),
                    matcher.start(),
                    matcher.end(),
                    finalScore
                ));
            }

            return entities;
        }
    }

    // =========================================================================
    // Hong Kong Phone Recognizer
    // =========================================================================

    /**
     * Recognize Hong Kong phone numbers.
     * Format: 8 digits starting with 5/6/7/8/9
     */
    public static class HongKongPhoneRecognizer {
        private static final Pattern PATTERN = Pattern.compile("(?<!\\d)([5-9]\\d{7})(?!\\d)");
        private static final Pattern PATTERN_FORMATTED = Pattern.compile("(?<!\\d)([5-9]\\d{3})[\\s-]?(\\d{4})(?!\\d)");
        private static final Pattern PATTERN_INTL = Pattern.compile("(?:\\+?852)[\\s-]?([5-9]\\d{7})");
        private static final double SCORE = 0.85;

        private static final Set<String> CONTEXT = Set.of(
            // Simplified Chinese
            "手机", "电话", "联系电话", "联系方式", "手机号",
            // Traditional Chinese (Hong Kong)
            "手機", "手機號", "手機號碼", "電話", "電話號碼", "聯絡電話", "流動電話",
            // English
            "mobile", "phone", "telephone", "tel", "contact", "cell", "hotline"
        );

        public List<PIIEntity> detect(String text) {
            List<PIIEntity> entities = new ArrayList<>();

            // Check international format
            Matcher matcherIntl = PATTERN_INTL.matcher(text);
            while (matcherIntl.find()) {
                entities.add(new PIIEntity(
                    PIIEntity.Type.PHONE,
                    matcherIntl.group(),
                    matcherIntl.start(),
                    matcherIntl.end(),
                    0.95
                ));
            }

            // Check basic format (only if not already matched)
            Matcher matcher = PATTERN.matcher(text);
            while (matcher.find()) {
                if (!alreadyMatched(entities, matcher.start(), matcher.end())) {
                    double finalScore = hasContext(text, matcher.start(), CONTEXT)
                        ? SCORE + 0.1
                        : SCORE;

                    entities.add(new PIIEntity(
                        PIIEntity.Type.PHONE,
                        matcher.group(),
                        matcher.start(),
                        matcher.end(),
                        finalScore
                    ));
                }
            }

            return entities;
        }
    }

    // =========================================================================
    // Hong Kong ID Card Recognizer
    // =========================================================================

    /**
     * Recognize Hong Kong ID card numbers.
     * Format: 1-2 letters + 6 digits + (checksum)
     * Example: A123456(7), AB123456(A)
     */
    public static class HongKongIDCardRecognizer {
        private static final Pattern PATTERN = Pattern.compile(
            "(?<![A-Za-z0-9])([A-Z]{1,2}\\d{6}\\([0-9A-Z]\\))(?![A-Za-z0-9)])"
        );
        private static final double SCORE = 0.95;

        private static final Set<String> CONTEXT = Set.of(
            // Simplified Chinese
            "身份证", "身份证号", "证件号", "香港身份证", "HKID",
            // Traditional Chinese (Hong Kong)
            "身份證", "身份證號碼", "身份證字號", "證件號", "香港身份證",
            // English
            "ID", "ID card", "HKID", "HK ID", "Hong Kong ID", "identity card"
        );

        public List<PIIEntity> detect(String text) {
            List<PIIEntity> entities = new ArrayList<>();
            Matcher matcher = PATTERN.matcher(text);

            while (matcher.find()) {
                double finalScore = hasContext(text, matcher.start(), CONTEXT)
                    ? SCORE
                    : SCORE * 0.8;

                entities.add(new PIIEntity(
                    PIIEntity.Type.ID_CARD,
                    matcher.group(),
                    matcher.start(),
                    matcher.end(),
                    finalScore
                ));
            }

            return entities;
        }
    }

    // =========================================================================
    // Helper Methods
    // =========================================================================

    /**
     * Check if context keywords appear within 50 characters before the match.
     */
    private static boolean hasContext(String text, int matchStart, Set<String> contextKeywords) {
        int windowStart = Math.max(0, matchStart - 50);
        String contextWindow = text.substring(windowStart, matchStart).toLowerCase();

        for (String keyword : contextKeywords) {
            if (contextWindow.contains(keyword.toLowerCase())) {
                return true;
            }
        }

        return false;
    }

    /**
     * Check if a position is already covered by existing entities.
     */
    private static boolean alreadyMatched(List<PIIEntity> entities, int start, int end) {
        for (PIIEntity entity : entities) {
            if (entity.getStart() <= start && entity.getEnd() >= end) {
                return true;
            }
        }
        return false;
    }
}
