package com.harness.memory;

import java.util.ArrayList;
import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.core.TokenCounter;
import com.harness.types.Message;

/**
 * Compresses conversation context to fit within token budget.
 *
 * Strategies (in order):
 * 1. Remove old messages beyond keepRecentMessages
 * 2. Generate summary of removed messages
 * 3. Truncate long tool results
 *
 * Example:
 * <pre>
 * TokenCounter counter = new TokenCounter();
 * ContextCompressor compressor = new ContextCompressor(counter);
 * CompressionResult result = compressor.compress(messages, 50000);
 * List<Message> compressed = result.compressedMessages();
 * </pre>
 */
public class ContextCompressor {

    private static final Logger logger = LoggerFactory.getLogger(ContextCompressor.class);

    private final TokenCounter tokenCounter;
    private final CompressionConfig config;

    public ContextCompressor(TokenCounter tokenCounter) {
        this(tokenCounter, CompressionConfig.defaults());
    }

    public ContextCompressor(TokenCounter tokenCounter, CompressionConfig config) {
        this.tokenCounter = tokenCounter;
        this.config = config;
    }

    /**
     * Compress messages to fit within target tokens.
     *
     * @param messages     All messages to potentially compress
     * @param targetTokens Target token count
     * @return CompressionResult with compressed messages and metadata
     */
    public CompressionResult compress(List<Message> messages, int targetTokens) {
        return compress(messages, targetTokens, null);
    }

    /**
     * Compress messages to fit within target tokens.
     *
     * @param messages        All messages to potentially compress
     * @param targetTokens    Target token count
     * @param systemMessages  Optional separate system messages (preserved)
     * @return CompressionResult with compressed messages and metadata
     */
    public CompressionResult compress(List<Message> messages, int targetTokens, List<Message> systemMessages) {
        if (messages.size() < config.minMessagesBeforeCompress()) {
            int tokens = countTokens(messages);
            return CompressionResult.builder()
                .originalMessages(messages)
                .compressedMessages(messages)
                .tokensBefore(tokens)
                .tokensAfter(tokens)
                .build();
        }

        int tokensBefore = countTokens(messages);

        if (tokensBefore <= targetTokens) {
            return CompressionResult.builder()
                .originalMessages(messages)
                .compressedMessages(messages)
                .tokensBefore(tokensBefore)
                .tokensAfter(tokensBefore)
                .build();
        }

        // Strategy 1: Keep recent messages, summarize older ones
        SummaryPair result = compressWithSummary(messages, targetTokens);

        List<Message> compressed = result.compressed();
        String summary = result.summary();
        int tokensAfter = countTokens(compressed);

        return CompressionResult.builder()
            .originalMessages(messages)
            .compressedMessages(compressed)
            .summary(summary)
            .tokensBefore(tokensBefore)
            .tokensAfter(tokensAfter)
            .messagesRemoved(messages.size() - compressed.size())
            .build();
    }

    /**
     * Compress by keeping recent messages and summarizing older ones.
     */
    private SummaryPair compressWithSummary(List<Message> messages, int targetTokens) {
        int keepCount = config.keepRecentMessages();

        // Always keep the most recent messages
        List<Message> recentMessages = messages.size() > keepCount
            ? new ArrayList<>(messages.subList(messages.size() - keepCount, messages.size()))
            : new ArrayList<>(messages);
        List<Message> oldMessages = messages.size() > keepCount
            ? new ArrayList<>(messages.subList(0, messages.size() - keepCount))
            : new ArrayList<>();

        if (oldMessages.isEmpty()) {
            return new CompressionResult.SummaryPair(messages, null);
        }

        // Generate summary of old messages
        String summary = generateSummary(oldMessages);

        // Check if we're within budget
        List<Message> compressed = new ArrayList<>();
        if (summary != null && !summary.isEmpty()) {
            compressed.add(Message.system("[Previous conversation summary]\n" + summary));
        }
        compressed.addAll(recentMessages);

        return new CompressionResult.SummaryPair(compressed, summary);
    }

    /**
     * Generate a summary of messages.
     *
     * Uses simple heuristic summarization (not LLM-based for MVP).
     * For production, this could be enhanced to use LLM summarization.
     */
    private String generateSummary(List<Message> messages) {
        if (messages.isEmpty()) {
            return "";
        }

        List<String> summaryParts = new ArrayList<>();

        // Track key information
        List<String> userRequests = new ArrayList<>();
        List<String> assistantActions = new ArrayList<>();
        List<String> toolCalls = new ArrayList<>();

        for (Message msg : messages) {
            String content = msg.contentAsString();

            switch (msg.role()) {
                case "user" -> {
                    // Capture user requests (truncate long ones)
                    String preview = content.length() > 200
                        ? content.substring(0, 200) + "..."
                        : content;
                    userRequests.add("- User asked: " + preview);
                }
                case "assistant" -> {
                    // Capture assistant responses
                    String preview = content.length() > 200
                        ? content.substring(0, 200) + "..."
                        : content;
                    assistantActions.add("- Assistant: " + preview);
                }
                case "tool" -> {
                    // Note tool usage
                    String toolName = msg.metadata() != null
                        ? (String) msg.metadata().getOrDefault("tool_name", "unknown")
                        : "unknown";
                    toolCalls.add("- Tool: " + toolName);
                }
            }
        }

        // Build summary
        if (!userRequests.isEmpty()) {
            summaryParts.add("### User Requests");
            // Keep last 5
            int start = Math.max(0, userRequests.size() - 5);
            summaryParts.addAll(userRequests.subList(start, userRequests.size()));
        }

        if (!assistantActions.isEmpty()) {
            summaryParts.add("\n### Key Actions");
            int start = Math.max(0, assistantActions.size() - 5);
            summaryParts.addAll(assistantActions.subList(start, assistantActions.size()));
        }

        if (!toolCalls.isEmpty()) {
            summaryParts.add("\n### Tools Used");
            int start = Math.max(0, toolCalls.size() - 10);
            summaryParts.addAll(toolCalls.subList(start, toolCalls.size()));
        }

        String summary = String.join("\n", summaryParts);

        // Truncate if too long
        int maxSummaryChars = config.summaryMaxTokens() * 4; // Rough char estimate
        if (summary.length() > maxSummaryChars) {
            summary = summary.substring(0, maxSummaryChars) + "\n... (truncated)";
        }

        return summary;
    }

    /**
     * Count total tokens in messages.
     */
    private int countTokens(List<Message> messages) {
        return tokenCounter.countMessages(messages);
    }

    /**
     * Determine if compression is needed.
     *
     * @param messages      Current messages
     * @param currentTokens Current token count
     * @param maxTokens     Maximum allowed tokens
     * @return True if compression is recommended
     */
    public boolean shouldCompress(List<Message> messages, int currentTokens, int maxTokens) {
        if (messages.size() < config.minMessagesBeforeCompress()) {
            return false;
        }
        return currentTokens > maxTokens;
    }

    /**
     * Internal helper for compression result.
     */
    private static class SummaryPair {
        private final List<Message> compressed;
        private final String summary;

        SummaryPair(List<Message> compressed, String summary) {
            this.compressed = compressed;
            this.summary = summary;
        }

        List<Message> compressed() { return compressed; }
        String summary() { return summary; }
    }
}
