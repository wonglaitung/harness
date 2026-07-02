package com.harness.memory;

/**
 * Token budget allocation for context components.
 *
 * Priority order: system_prompt > recent_messages > skills > memory
 */
public class ContextBudget {

    private final int maxTokens;
    private final int responseReserve;
    private final int systemPrompt;
    private final int tools;
    private final int recentMessages;
    private final int skills;
    private final int memory;

    public ContextBudget() {
        this(200000, 4096, 0, 0, 0, 0, 0);
    }

    public ContextBudget(
        int maxTokens,
        int responseReserve,
        int systemPrompt,
        int tools,
        int recentMessages,
        int skills,
        int memory
    ) {
        this.maxTokens = maxTokens;
        this.responseReserve = responseReserve;
        this.systemPrompt = systemPrompt;
        this.tools = tools;
        this.recentMessages = recentMessages;
        this.skills = skills;
        this.memory = memory;
    }

    /**
     * Tokens available for all input components.
     */
    public int availableForInput() {
        return maxTokens - responseReserve;
    }

    /**
     * Total tokens allocated.
     */
    public int used() {
        return systemPrompt + tools + recentMessages + skills + memory;
    }

    /**
     * Tokens remaining unallocated.
     */
    public int remaining() {
        return availableForInput() - used();
    }

    /**
     * Check if context exceeds budget and needs compression.
     */
    public boolean needsCompression() {
        return used() > availableForInput();
    }

    /**
     * Create a budget with automatic allocation.
     *
     * @param maxTokens           Maximum context window
     * @param systemPromptTokens  Actual system prompt tokens
     * @param toolTokens          Actual tool definition tokens
     * @param messageRatio        Ratio for messages (default 0.7)
     * @param skillsRatio         Ratio for skills (default 0.2)
     * @param memoryRatio         Ratio for memory (default 0.1)
     */
    public static ContextBudget allocate(
        int maxTokens,
        int systemPromptTokens,
        int toolTokens,
        double messageRatio,
        double skillsRatio,
        double memoryRatio
    ) {
        int responseReserve = 4096;
        int available = maxTokens - responseReserve;

        // Fixed allocations first (high priority)
        int actualSystem = Math.min(systemPromptTokens, available);
        int remainingAfterSystem = available - actualSystem;

        int actualTools = Math.min(toolTokens, remainingAfterSystem);
        int remaining = remainingAfterSystem - actualTools;

        // Proportional allocation for remaining
        double totalRatio = messageRatio + skillsRatio + memoryRatio;
        int messagesAlloc;
        int skillsAlloc;
        int memoryAlloc;

        if (totalRatio > 0) {
            messagesAlloc = (int) (remaining * messageRatio / totalRatio);
            skillsAlloc = (int) (remaining * skillsRatio / totalRatio);
            memoryAlloc = remaining - messagesAlloc - skillsAlloc;
        } else {
            messagesAlloc = remaining;
            skillsAlloc = 0;
            memoryAlloc = 0;
        }

        return new ContextBudget(
            maxTokens,
            responseReserve,
            actualSystem,
            actualTools,
            messagesAlloc,
            skillsAlloc,
            memoryAlloc
        );
    }

    /**
     * Simplified allocation with default ratios.
     */
    public static ContextBudget allocate(int maxTokens, int systemPromptTokens, int toolTokens) {
        return allocate(maxTokens, systemPromptTokens, toolTokens, 0.7, 0.2, 0.1);
    }

    // Getters

    public int maxTokens() { return maxTokens; }
    public int responseReserve() { return responseReserve; }
    public int systemPrompt() { return systemPrompt; }
    public int tools() { return tools; }
    public int recentMessages() { return recentMessages; }
    public int skills() { return skills; }
    public int memory() { return memory; }
}