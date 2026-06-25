package com.harness.core;

import java.util.Map;

import com.harness.types.TokenUsage;

/**
 * Result from a sub-agent execution.
 */
public record SubAgentResult(
    String name,
    boolean success,
    SubAgentStatus status,
    String summary,
    String fullResponse,
    Map<String, Object> structuredResult,
    int iterations,
    TokenUsage tokenUsage,
    String error
) {

    /**
     * Create a successful result.
     */
    public static SubAgentResult success(String name, String summary, int iterations, TokenUsage tokenUsage) {
        return new SubAgentResult(name, true, SubAgentStatus.COMPLETED, summary, null, null, iterations, tokenUsage, null);
    }

    /**
     * Create a failed result.
     */
    public static SubAgentResult failure(String name, String error) {
        return new SubAgentResult(name, false, SubAgentStatus.FAILED, null, null, null, 0, null, error);
    }

    /**
     * Create a cancelled result.
     */
    public static SubAgentResult cancelled(String name) {
        return new SubAgentResult(name, false, SubAgentStatus.CANCELLED, null, null, null, 0, null, "Cancelled by user");
    }
}
