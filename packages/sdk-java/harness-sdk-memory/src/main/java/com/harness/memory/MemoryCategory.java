package com.harness.memory;

/**
 * Categories for memory entries.
 */
public enum MemoryCategory {
    USER_PROFILE("User Profile"),
    KEY_DECISIONS("Key Decisions"),
    LEARNED_PATTERNS("Learned Patterns"),
    PROJECT_CONTEXT("Project Context");

    private final String header;

    MemoryCategory(String header) {
        this.header = header;
    }

    public String getHeader() {
        return header;
    }

    public static MemoryCategory fromHeader(String header) {
        for (MemoryCategory cat : values()) {
            if (cat.header.equals(header)) {
                return cat;
            }
        }
        return PROJECT_CONTEXT;
    }
}