package com.harness.memory;

import java.util.List;

import com.harness.types.Message;

/**
 * Result of context building.
 */
public class BuiltContext {

    private final List<Message> messages;
    private final String systemPrompt;
    private final int estimatedTokens;
    private final ContextBudget budget;
    private final boolean compressionNeeded;
    private final CompressionResult compressionResult;

    public BuiltContext(
        List<Message> messages,
        String systemPrompt,
        int estimatedTokens,
        ContextBudget budget,
        boolean compressionNeeded,
        CompressionResult compressionResult
    ) {
        this.messages = messages;
        this.systemPrompt = systemPrompt;
        this.estimatedTokens = estimatedTokens;
        this.budget = budget;
        this.compressionNeeded = compressionNeeded;
        this.compressionResult = compressionResult;
    }

    /**
     * Messages ready for LLM call.
     */
    public List<Message> messages() { return messages; }

    /**
     * System prompt (may include compression summary if applied).
     */
    public String systemPrompt() { return systemPrompt; }

    /**
     * Estimated token count.
     */
    public int estimatedTokens() { return estimatedTokens; }

    /**
     * Token budget allocation.
     */
    public ContextBudget budget() { return budget; }

    /**
     * Whether compression was needed.
     */
    public boolean compressionNeeded() { return compressionNeeded; }

    /**
     * Compression result if compression was performed.
     */
    public CompressionResult compressionResult() { return compressionResult; }

    /**
     * Check if near token limit.
     */
    public boolean isNearLimit() {
        return budget != null && budget.remaining() < 1000;
    }
}