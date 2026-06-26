package com.harness.guardrails;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Chinese Name Recognizer.
 *
 * Provides Chinese name detection using surname lists and rules.
 * Supports both single-character and compound surnames.
 *
 * Example:
 * <pre>
 * ChineseNameRecognizer recognizer = new ChineseNameRecognizer();
 * List&lt;NameMatch&gt; names = recognizer.recognize("联系人：张伟，电话13912345678");
 * // [NameMatch(text='张伟', surname='张', given_name='伟', score=0.9)]
 * </pre>
 */
public class ChineseNameRecognizer {

    // Common Chinese surnames (top 100, covering ~85% of population)
    private static final Set<Character> COMMON_SURNAMES = Set.of(
        '王', '李', '张', '刘', '陈', '杨', '赵', '黄', '周', '吴',
        '徐', '孙', '胡', '朱', '高', '林', '何', '郭', '马', '罗',
        '梁', '宋', '郑', '谢', '韩', '唐', '冯', '于', '董', '萧',
        '程', '曹', '袁', '邓', '许', '傅', '沈', '曾', '彭', '吕',
        '苏', '卢', '蒋', '蔡', '贾', '丁', '魏', '薛', '叶', '阎',
        '余', '潘', '杜', '戴', '夏', '钟', '汪', '田', '任', '姜',
        '范', '方', '石', '姚', '谭', '廖', '邹', '熊', '金', '陆',
        '郝', '孔', '白', '崔', '康', '毛', '邱', '秦', '江', '史',
        '顾', '侯', '邵', '孟', '龙', '万', '段', '曹', '钱', '汤',
        '尹', '黎', '易', '常', '武', '乔', '贺', '赖', '龚', '文'
    );

    // Compound surnames (two-character surnames)
    private static final List<String> COMPOUND_SURNAMES = List.of(
        "欧阳", "上官", "司马", "诸葛", "东方", "皇甫", "尉迟", "公孙", "令狐", "宇文",
        "长孙", "慕容", "司徒", "南宫", "独孤", "百里", "端木", "轩辕", "赫连", "澹台"
    );

    // False positives to filter out
    private static final Set<String> FALSE_POSITIVES = Set.of(
        // Common non-name phrases
        "手机号", "电话号", "身份证", "银行卡", "邮箱地", "联系方",
        "公司名", "产品名", "用户名", "账号", "账户",
        // City names
        "北京市", "上海市", "广州市", "深圳市",
        // Days of week
        "周一", "周二", "周三", "周四", "周五", "周六", "周日",
        // Months
        "一月", "二月", "三月", "四月", "五月", "六月",
        "七月", "八月", "九月", "十月", "十一月", "十二月"
    );

    // Common given name characters
    private static final Set<Character> COMMON_GIVEN_CHARS = Set.of(
        '伟', '芳', '娜', '敏', '静', '丽', '强', '磊', '军', '洋',
        '勇', '艳', '杰', '娟', '涛', '明', '超', '秀', '霞', '平',
        '刚', '桂', '英', '兰', '华', '建', '国', '文', '辉', '斌',
        '波', '宇', '红', '梅', '玲', '鹏', '峰', '毅', '浩', '清',
        '云', '翔', '林', '海', '天', '山', '风', '龙', '飞'
    );

    // Context keywords that indicate names
    private static final Set<String> NAME_CONTEXT = Set.of(
        "姓名", "名字", "联系人", "联系", "客户", "用户", "本人", "持卡人",
        "叫", "是", "叫作", "叫做"
    );

    // Patterns for name detection
    private static final Pattern[] NAME_PATTERNS = {
        // Context keyword + name
        Pattern.compile("(?:姓名|名字|联系人|联系|客户|用户|本人|持卡人|叫|是)[:：]?\\s*([\\u4e00-\\u9fff]{2,4})"),
        // Name + possessive + other info
        Pattern.compile("([\\u4e00-\\u9fff]{2,3})的(?:手机|电话|邮箱|身份证|银行卡)"),
        // Standalone 2-4 character Chinese name
        Pattern.compile("(?<![\\u4e00-\\u9fff])([\\u4e00-\\u9fff]{2,4})(?![\\u4e00-\\u9fff])")
    };

    private final double minScore;

    /**
     * Create a Chinese name recognizer with default settings.
     */
    public ChineseNameRecognizer() {
        this(0.5);
    }

    /**
     * Create a Chinese name recognizer.
     *
     * @param minScore Minimum confidence threshold
     */
    public ChineseNameRecognizer(double minScore) {
        this.minScore = minScore;
    }

    /**
     * Recognize Chinese names in text.
     *
     * @param text Text to analyze
     * @return List of detected name matches
     */
    public List<NameMatch> recognize(String text) {
        List<NameMatch> results = new ArrayList<>();

        for (Pattern pattern : NAME_PATTERNS) {
            Matcher matcher = pattern.matcher(text);
            while (matcher.find()) {
                String candidate = matcher.group(1);
                int start = matcher.start(1);
                int end = matcher.end(1);

                NameMatch nameMatch = validateName(candidate, start, end, text);
                if (nameMatch != null && nameMatch.score >= minScore) {
                    // Check for duplicates
                    if (!isDuplicate(results, nameMatch)) {
                        results.add(nameMatch);
                    }
                }
            }
        }

        return results;
    }

    /**
     * Detect Chinese names and return as PII entities.
     *
     * @param text Text to analyze
     * @return List of PII entities
     */
    public List<PIIEntity> detect(String text) {
        List<PIIEntity> entities = new ArrayList<>();
        List<NameMatch> names = recognize(text);

        for (NameMatch name : names) {
            entities.add(new PIIEntity(
                PIIEntity.Type.NAME,
                name.text,
                name.start,
                name.end,
                name.score
            ));
        }

        return entities;
    }

    /**
     * Validate if a candidate string is a valid Chinese name.
     */
    private NameMatch validateName(String candidate, int start, int end, String fullText) {
        if (candidate == null || candidate.isEmpty()) {
            return null;
        }

        // Length check (2-4 characters)
        if (candidate.length() < 2 || candidate.length() > 4) {
            return null;
        }

        // Must be all Chinese characters
        for (char c : candidate.toCharArray()) {
            if (c < '\u4e00' || c > '\u9fff') {
                return null;
            }
        }

        // Check for false positives
        if (FALSE_POSITIVES.contains(candidate)) {
            return null;
        }

        // Check surname
        String surname = null;
        String givenName = null;

        // Check compound surnames first
        for (String cs : COMPOUND_SURNAMES) {
            if (candidate.startsWith(cs)) {
                surname = cs;
                givenName = candidate.substring(cs.length());
                break;
            }
        }

        // Check single-character surnames
        if (surname == null) {
            char firstChar = candidate.charAt(0);
            if (COMMON_SURNAMES.contains(firstChar)) {
                surname = String.valueOf(firstChar);
                givenName = candidate.substring(1);
            }
        }

        if (surname == null) {
            return null;
        }

        // Calculate score
        double score = calculateScore(candidate, surname, givenName, fullText, start);

        return new NameMatch(candidate, start, end, score, surname, givenName);
    }

    /**
     * Calculate confidence score for a name.
     */
    private double calculateScore(String candidate, String surname, String givenName,
                                   String fullText, int matchStart) {
        double score = 0.7;

        // Bonus for common surname
        if (COMMON_SURNAMES.contains(surname.charAt(0)) || COMPOUND_SURNAMES.contains(surname)) {
            score += 0.1;
        }

        // Bonus for reasonable given name length (1-2 chars)
        if (givenName != null && givenName.length() >= 1 && givenName.length() <= 2) {
            score += 0.1;
        }

        // Bonus for common given name characters
        if (givenName != null) {
            boolean allCommon = true;
            for (char c : givenName.toCharArray()) {
                if (!COMMON_GIVEN_CHARS.contains(c)) {
                    allCommon = false;
                    break;
                }
            }
            if (allCommon) {
                score += 0.05;
            }
        }

        // Bonus for context keywords
        if (hasContext(fullText, matchStart, NAME_CONTEXT)) {
            score += 0.1;
        }

        return Math.min(score, 1.0);
    }

    /**
     * Check if context keywords appear within 30 characters before the match.
     */
    private boolean hasContext(String text, int matchStart, Set<String> contextKeywords) {
        int windowStart = Math.max(0, matchStart - 30);
        String contextWindow = text.substring(windowStart, matchStart).toLowerCase();

        for (String keyword : contextKeywords) {
            if (contextWindow.contains(keyword.toLowerCase())) {
                return true;
            }
        }

        return false;
    }

    /**
     * Check if a match is a duplicate of existing results.
     */
    private boolean isDuplicate(List<NameMatch> results, NameMatch newMatch) {
        for (NameMatch existing : results) {
            // Consider it a duplicate if there's significant overlap
            if (newMatch.start < existing.end && newMatch.end > existing.start) {
                return true;
            }
        }
        return false;
    }

    /**
     * Name match result.
     */
    public static class NameMatch {
        public final String text;
        public final int start;
        public final int end;
        public final double score;
        public final String surname;
        public final String givenName;

        public NameMatch(String text, int start, int end, double score, String surname, String givenName) {
            this.text = text;
            this.start = start;
            this.end = end;
            this.score = score;
            this.surname = surname;
            this.givenName = givenName;
        }

        @Override
        public String toString() {
            return String.format("NameMatch{text='%s', surname='%s', given='%s', score=%.2f}",
                text, surname, givenName, score);
        }
    }
}
