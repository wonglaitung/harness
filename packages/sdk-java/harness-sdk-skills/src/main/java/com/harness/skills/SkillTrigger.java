package com.harness.skills;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;

/**
 * Skill trigger conditions.
 *
 * Defines when a skill should be activated based on:
 * - Keywords: Simple text matching
 * - Patterns: Regex pattern matching
 * - Tools: Tool call triggers
 *
 * Example:
 * <pre>
 * SkillTrigger trigger = new SkillTrigger(
 *     List.of("analyze", "review"),
 *     List.of("analyze\\s+\\w+"),
 *     List.of("read", "grep")
 * );
 *
 * if (trigger.matches("Please analyze this code")) {
 *     // Activate skill
 * }
 * </pre>
 */
public class SkillTrigger {

    private final List<String> keywords;
    private final List<String> patterns;
    private final List<String> tools;

    /**
     * Create a skill trigger.
     *
     * @param keywords Keywords to match (case-insensitive)
     * @param patterns Regex patterns to match
     * @param tools Tool names that trigger this skill
     */
    public SkillTrigger(List<String> keywords, List<String> patterns, List<String> tools) {
        this.keywords = keywords != null ? new ArrayList<>(keywords) : List.of();
        this.patterns = patterns != null ? new ArrayList<>(patterns) : List.of();
        this.tools = tools != null ? new ArrayList<>(tools) : List.of();
    }

    /**
     * Create an empty trigger.
     */
    public SkillTrigger() {
        this(List.of(), List.of(), List.of());
    }

    /**
     * Create a trigger with only keywords.
     */
    public static SkillTrigger keywords(String... keywords) {
        return new SkillTrigger(List.of(keywords), List.of(), List.of());
    }

    /**
     * Create a trigger with only patterns.
     */
    public static SkillTrigger patterns(String... patterns) {
        return new SkillTrigger(List.of(), List.of(patterns), List.of());
    }

    /**
     * Create a trigger with only tools.
     */
    public static SkillTrigger tools(String... tools) {
        return new SkillTrigger(List.of(), List.of(), List.of(tools));
    }

    /**
     * Check if text matches trigger conditions.
     *
     * @param text User input text to check
     * @return True if any trigger condition matches
     */
    public boolean matches(String text) {
        if (text == null || text.isEmpty()) {
            return false;
        }

        String textLower = text.toLowerCase();

        // Keyword matching (case-insensitive)
        for (String keyword : keywords) {
            if (textLower.contains(keyword.toLowerCase())) {
                return true;
            }
        }

        // Regex pattern matching
        for (String pattern : patterns) {
            try {
                if (Pattern.compile(pattern, Pattern.CASE_INSENSITIVE).matcher(text).find()) {
                    return true;
                }
            } catch (PatternSyntaxException e) {
                // Invalid regex pattern, skip
                continue;
            }
        }

        return false;
    }

    /**
     * Check if a tool call triggers this skill.
     *
     * @param toolName Tool name being called
     * @return True if the tool is in the trigger list
     */
    public boolean triggersOnTool(String toolName) {
        if (toolName == null || toolName.isEmpty()) {
            return false;
        }
        return tools.contains(toolName);
    }

    /**
     * Check if this trigger has any conditions.
     *
     * @return True if no trigger conditions are defined
     */
    public boolean isEmpty() {
        return keywords.isEmpty() && patterns.isEmpty() && tools.isEmpty();
    }

    /**
     * Builder for creating triggers.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private List<String> keywords = new ArrayList<>();
        private List<String> patterns = new ArrayList<>();
        private List<String> tools = new ArrayList<>();

        public Builder keywords(List<String> keywords) {
            this.keywords = new ArrayList<>(keywords);
            return this;
        }

        public Builder addKeyword(String keyword) {
            this.keywords.add(keyword);
            return this;
        }

        public Builder patterns(List<String> patterns) {
            this.patterns = new ArrayList<>(patterns);
            return this;
        }

        public Builder addPattern(String pattern) {
            this.patterns.add(pattern);
            return this;
        }

        public Builder tools(List<String> tools) {
            this.tools = new ArrayList<>(tools);
            return this;
        }

        public Builder addTool(String tool) {
            this.tools.add(tool);
            return this;
        }

        public SkillTrigger build() {
            return new SkillTrigger(keywords, patterns, tools);
        }
    }

    // Getters
    public List<String> keywords() { return keywords; }
    public List<String> patterns() { return patterns; }
    public List<String> tools() { return tools; }

    @Override
    public String toString() {
        return String.format("SkillTrigger(keywords=%s, patterns=%s, tools=%s)",
            keywords, patterns.size() + " patterns", tools);
    }
}
