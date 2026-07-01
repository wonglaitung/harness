package com.harness.loop.types;

/**
 * Method used for goal verification.
 */
public enum VerificationMethod {
    /**
     * LLM-based verification.
     * Uses the LLM to determine if the goal has been achieved.
     */
    LLM("llm"),

    /**
     * User-provided custom verification function.
     */
    CUSTOM("custom"),

    /**
     * Tool-based verification (tests, lint, type check, etc.).
     */
    TOOL("tool");

    private final String value;

    VerificationMethod(String value) {
        this.value = value;
    }

    /**
     * Get the string value of the method.
     *
     * @return String representation
     */
    public String getValue() {
        return value;
    }

    /**
     * Parse from string value.
     *
     * @param value String value to parse
     * @return VerificationMethod or null if not found
     */
    public static VerificationMethod fromValue(String value) {
        for (VerificationMethod method : values()) {
            if (method.value.equals(value)) {
                return method;
            }
        }
        return null;
    }
}
