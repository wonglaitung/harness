package com.harness.skills;

/**
 * Configuration for skill injection.
 *
 * Controls how skills are injected into system prompts.
 */
public record InjectionConfig(
    int maxSkillsPerPrompt,
    int maxSkillLength,
    int warnSkillLength,
    String injectMethod,
    String skillSeparator
) {

    public InjectionConfig() {
        this(5, 0, 8000, "append", "\n\n---\n\n");
    }

    /**
     * Create default configuration.
     */
    public static InjectionConfig defaults() {
        return new InjectionConfig();
    }

    /**
     * Create builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private int maxSkillsPerPrompt = 5;
        private int maxSkillLength = 0;  // 0 = no limit, user controls via logging
        private int warnSkillLength = 8000;  // Log warning if skill exceeds this length
        private String injectMethod = "append";  // append, prepend, section
        private String skillSeparator = "\n\n---\n\n";

        public Builder maxSkillsPerPrompt(int value) {
            this.maxSkillsPerPrompt = value;
            return this;
        }

        public Builder maxSkillLength(int value) {
            this.maxSkillLength = value;
            return this;
        }

        public Builder warnSkillLength(int value) {
            this.warnSkillLength = value;
            return this;
        }

        public Builder injectMethod(String value) {
            this.injectMethod = value;
            return this;
        }

        public Builder skillSeparator(String value) {
            this.skillSeparator = value;
            return this;
        }

        public InjectionConfig build() {
            return new InjectionConfig(
                maxSkillsPerPrompt,
                maxSkillLength,
                warnSkillLength,
                injectMethod,
                skillSeparator
            );
        }
    }
}
