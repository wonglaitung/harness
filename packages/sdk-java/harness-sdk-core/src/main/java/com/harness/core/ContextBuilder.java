package com.harness.core;

import java.util.ArrayList;
import java.util.List;

import com.harness.types.Message;
import com.harness.types.Session;

/**
 * Context builder - builds the context for LLM calls.
 */
public class ContextBuilder {

    private final int contextWindow;
    private final double memoryRatio;
    private final TokenCounter tokenCounter;

    public ContextBuilder(int contextWindow, double memoryRatio) {
        this.contextWindow = contextWindow;
        this.memoryRatio = memoryRatio;
        this.tokenCounter = new TokenCounter();
    }

    public ContextBuilder(int contextWindow) {
        this(contextWindow, 0.3);
    }

    public ContextBuilder() {
        this(200_000, 0.3); // Default: 200k context window, 30% for memory
    }

    /**
     * Build context from session.
     */
    public Context build(Session session) {
        List<Message> messages = new ArrayList<>();

        // 1. System prompt
        String systemPrompt = buildSystemPrompt(session);

        // 2. Truncate history to fit within token budget
        int maxContextTokens = (int) (contextWindow * (1 - memoryRatio));
        List<Message> history = truncateHistory(session.messages(), maxContextTokens);
        messages.addAll(history);

        // 3. Calculate token usage
        int totalTokens = tokenCounter.countMessages(messages);
        int remaining = contextWindow - totalTokens;

        return new Context(messages, systemPrompt, totalTokens, remaining);
    }

    /**
     * Build system prompt.
     */
    private String buildSystemPrompt(Session session) {
        StringBuilder sb = new StringBuilder();

        // Base system prompt
        if (session.systemPrompt() != null && !session.systemPrompt().isEmpty()) {
            sb.append(session.systemPrompt()).append("\n\n");
        }

        // Working directory info
        sb.append("Working directory: ").append(System.getProperty("user.dir")).append("\n");

        return sb.toString();
    }

    /**
     * Truncate history to fit within token budget.
     */
    private List<Message> truncateHistory(List<Message> messages, int maxTokens) {
        List<Message> result = new ArrayList<>();
        int currentTokens = 0;

        // Add messages from newest to oldest
        for (int i = messages.size() - 1; i >= 0; i--) {
            Message msg = messages.get(i);
            int msgTokens = tokenCounter.count(msg.contentAsString());

            if (currentTokens + msgTokens > maxTokens) {
                // If exceeding budget, add truncation notice
                if (i > 0) {
                    result.add(0, Message.system("... " + i + " earlier messages omitted ..."));
                }
                break;
            }

            result.add(0, msg);
            currentTokens += msgTokens;
        }

        return result;
    }

    /**
     * Context result.
     */
    public record Context(
        List<Message> messages,
        String systemPrompt,
        int usedTokens,
        int remainingTokens
    ) {
        public boolean isNearLimit() {
            return remainingTokens < 1000;
        }
    }
}