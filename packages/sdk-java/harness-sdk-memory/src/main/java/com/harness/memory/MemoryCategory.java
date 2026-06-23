package com.harness.memory;

/**
 * Categories for memory entries.
 */
public enum MemoryCategory {
    USER_PROFILE("User Profile", "user_profile"),
    KEY_DECISIONS("Key Decisions", "key_decisions"),
    LEARNED_PATTERNS("Learned Patterns", "learned_patterns"),
    PROJECT_CONTEXT("Project Context", "project_context");

    private final String header;
    private final String value;

    MemoryCategory(String header, String value) {
        this.header = header;
        this.value = value;
    }

    public String getHeader() {
        return header;
    }

    /**
     * Get the lowercase value string (e.g., "user_profile").
     */
    public String getValue() {
        return value;
    }

    /**
     * Find category by header name.
     */
    public static MemoryCategory fromHeader(String header) {
        for (MemoryCategory cat : values()) {
            if (cat.header.equals(header)) {
                return cat;
            }
        }
        return PROJECT_CONTEXT;
    }

    /**
     * Find category by lowercase value string.
     */
    public static MemoryCategory fromValue(String value) {
        for (MemoryCategory cat : values()) {
            if (cat.value.equals(value)) {
                return cat;
            }
        }
        return PROJECT_CONTEXT;
    }
}