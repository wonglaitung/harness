package com.harness.core;

/**
 * Token budget allocation for context components.
 *
 * Priority order: system_prompt > recent_messages > skills > memory
 *
 * Example:
 * <pre>
 * ContextBudget budget = ContextBudget.allocate(200000, 1000, 2000);
 * System.out.println("Available for input: " + budget.availableForInput());
 * System.out.println("Remaining: " + budget.remaining());
 * </pre>
 */
public class ContextBudget {

    private final int maxTokens;
    private final int responseReserve;
    private int systemPrompt = 0;
    private int tools = 0;
    private int recentMessages = 0;
    private int skills = 0;
    private int memory = 0;

    public ContextBudget(int maxTokens, int responseReserve) {
        this.maxTokens = maxTokens;
        this.responseReserve = responseReserve;
    }

    public ContextBudget(int maxTokens) {
        this(maxTokens, 4096);
    }

    public ContextBudget() {
        this(200000, 4096);
    }

    // Getters
    public int maxTokens() { return maxTokens; }
    public int responseReserve() { return responseReserve; }
    public int systemPrompt() { return systemPrompt; }
    public int tools() { return tools; }
    public int recentMessages() { return recentMessages; }
    public int skills() { return skills; }
    public int memory() { return memory; }

    // Setters
    public ContextBudget systemPrompt(int v) { this.systemPrompt = v; return this; }
    public ContextBudget tools(int v) { this.tools = v; return this; }
    public ContextBudget recentMessages(int v) { this.recentMessages = v; return this; }
    public ContextBudget skills(int v) { this.skills = v; return this; }
    public ContextBudget memory(int v) { this.memory = v; return this; }

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
     * Check if usage exceeds threshold.
     */
    public boolean exceedsThreshold(double threshold) {
        return used() > availableForInput() * threshold;
    }

    /**
     * Create a budget with automatic allocation.
     *
     * @param maxTokens Maximum context window
     * @param systemPromptTokens Actual system prompt tokens
     * @param toolTokens Actual tool definition tokens
     * @return Allocated ContextBudget
     */
    public static ContextBudget allocate(
            int maxTokens,
            int systemPromptTokens,
            int toolTokens) {
        return allocate(maxTokens, systemPromptTokens, toolTokens, 0.7, 0.2, 0.1);
    }

    /**
     * Create a budget with automatic allocation and custom ratios.
     *
     * @param maxTokens Maximum context window
     * @param systemPromptTokens Actual system prompt tokens
     * @param toolTokens Actual tool definition tokens
     * @param messageRatio Ratio for messages (default 70%)
     * @param skillsRatio Ratio for skills (default 20%)
     * @param memoryRatio Ratio for memory (default 10%)
     * @return Allocated ContextBudget
     */
    public static ContextBudget allocate(
            int maxTokens,
            int systemPromptTokens,
            int toolTokens,
            double messageRatio,
            double skillsRatio,
            double memoryRatio) {

        int responseReserve = 4096;
        int available = maxTokens - responseReserve;

        // Fixed allocations first (high priority)
        int actualSystem = Math.min(systemPromptTokens, available);
        int remainingAfterSystem = available - actualSystem;

        int actualTools = Math.min(toolTokens, remainingAfterSystem);
        int remaining = remainingAfterSystem - actualTools;

        // Proportional allocation for remaining
        double totalRatio = messageRatio + skillsRatio + memoryRatio;
        int messagesAlloc, skillsAlloc, memoryAlloc;

        if (totalRatio > 0) {
            messagesAlloc = (int) (remaining * messageRatio / totalRatio);
            skillsAlloc = (int) (remaining * skillsRatio / totalRatio);
            memoryAlloc = remaining - messagesAlloc - skillsAlloc;
        } else {
            messagesAlloc = remaining;
            skillsAlloc = 0;
            memoryAlloc = 0;
        }

        ContextBudget budget = new ContextBudget(maxTokens, responseReserve);
        budget.systemPrompt = actualSystem;
        budget.tools = actualTools;
        budget.recentMessages = messagesAlloc;
        budget.skills = skillsAlloc;
        budget.memory = memoryAlloc;

        return budget;
    }

    /**
     * Create a builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private int maxTokens = 200000;
        private int responseReserve = 4096;
        private int systemPrompt = 0;
        private int tools = 0;
        private int recentMessages = 0;
        private int skills = 0;
        private int memory = 0;

        public Builder maxTokens(int v) { this.maxTokens = v; return this; }
        public Builder responseReserve(int v) { this.responseReserve = v; return this; }
        public Builder systemPrompt(int v) { this.systemPrompt = v; return this; }
        public Builder tools(int v) { this.tools = v; return this; }
        public Builder recentMessages(int v) { this.recentMessages = v; return this; }
        public Builder skills(int v) { this.skills = v; return this; }
        public Builder memory(int v) { this.memory = v; return this; }

        public ContextBudget build() {
            ContextBudget budget = new ContextBudget(maxTokens, responseReserve);
            budget.systemPrompt = systemPrompt;
            budget.tools = tools;
            budget.recentMessages = recentMessages;
            budget.skills = skills;
            budget.memory = memory;
            return budget;
        }
    }

    @Override
    public String toString() {
        return String.format(
            "ContextBudget{max=%d, used=%d, remaining=%d, system=%d, tools=%d, messages=%d, skills=%d, memory=%d}",
            maxTokens, used(), remaining(), systemPrompt, tools, recentMessages, skills, memory
        );
    }
}
