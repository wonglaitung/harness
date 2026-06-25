package com.harness.skills;

/**
 * Configuration for skill injection.
 *
 * Controls how skills are injected into system prompts.
 */
public record InjectionConfig(
    int maxSkillsPerPrompt,
    int maxSkillLength,
    String injectMethod,
    String skillSeparator
) {

    public InjectionConfig() {
        this(5, 2000, "append", "\n\n---\n\n");
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
        private int maxSkillLength = 2000;
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
                injectMethod,
                skillSeparator
            );
        }
    }
}
