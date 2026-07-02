package com.harness.memory;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.core.TokenCounter;
import com.harness.types.Message;
import com.harness.types.Session;

/**
 * Context builder for assembling messages for LLM calls.
 *
 * Handles system prompt injection, message windowing, and token budget management.
 * Includes automatic compression when context exceeds budget.
 *
 * Features:
 * - Dynamic system prompt assembly from multiple sources (AGENTS.md, MEMORY.md, etc.)
 * - Automatic compression when context exceeds budget
 * - Sliding window for message history
 * - Token budget allocation
 *
 * Example:
 * <pre>
 * ContextBuilder builder = new ContextBuilder()
 *     .withMaxTokens(200000)
 *     .withSystemPrompt("You are a helpful assistant.")
 *     .withProjectRoot(Path.of("/path/to/project"));
 *
 * BuiltContext context = builder.build(session);
 * String systemPrompt = context.systemPrompt();
 * List<Message> messages = context.messages();
 * </pre>
 */
public class ContextBuilder {

    private static final Logger logger = LoggerFactory.getLogger(ContextBuilder.class);

    private ContextConfig config;
    private final TokenCounter tokenCounter;
    private ContextCompressor compressor;
    private SystemPromptBuilder promptBuilder;

    public ContextBuilder() {
        this(ContextConfig.defaults());
    }

    public ContextBuilder(ContextConfig config) {
        this.config = config;
        this.tokenCounter = new TokenCounter();
        initCompressor();
        initSystemPromptBuilder();
    }

    /**
     * Initialize compressor based on config.
     */
    private void initCompressor() {
        if (config.enableCompression()) {
            CompressionConfig compressionConfig = config.compressionConfig() != null
                ? config.compressionConfig()
                : CompressionConfig.defaults();
            this.compressor = new ContextCompressor(tokenCounter, compressionConfig);
        } else {
            this.compressor = null;
        }
    }

    /**
     * Initialize system prompt builder based on config.
     */
    private void initSystemPromptBuilder() {
        if (config.systemPromptConfig() != null) {
            // Use provided config
            this.promptBuilder = new SystemPromptBuilder(config.systemPromptConfig());
        } else if (config.projectRoot() != null
                   || (config.systemPrompt() != null && !config.systemPrompt().isEmpty())
                   || config.memoryMdPath() != null) {
            // Create config from simple settings
            SystemPromptConfig promptConfig = SystemPromptConfig.builder()
                .basePrompt(config.systemPrompt())
                .projectRoot(config.projectRoot())
                .autoDiscover(true)
                .build();

            this.promptBuilder = new SystemPromptBuilder(promptConfig);

            // Add global memory source if specified
            if (config.memoryMdPath() != null) {
                Path memoryPath = config.memoryMdPath();
                // memoryMdPath can be either a directory or full file path
                if (memoryPath.toFile().isDirectory()) {
                    memoryPath = memoryPath.resolve("MEMORY.md");
                }
                this.promptBuilder.addSource(new SystemPromptSource(
                    "GlobalMemory",
                    40,
                    null,
                    memoryPath,
                    false
                ));
            }
        } else {
            // No dynamic prompt building
            this.promptBuilder = null;
        }
    }

    /**
     * Build context from session.
     *
     * @param session Current session
     * @return BuiltContext with messages and system prompt
     */
    public BuiltContext build(Session session) {
        return build(session, null, null);
    }

    /**
     * Build context from session with optional new prompt and tools.
     *
     * @param session    Current session
     * @param newPrompt  Optional new user prompt
     * @param tools      Available tools for budget estimation
     * @return BuiltContext with messages and system prompt
     */
    public BuiltContext build(Session session, String newPrompt, List<Object> tools) {
        // Build system prompt once (avoid duplicate build calls)
        String systemPrompt = getSystemPrompt();

        // Calculate budget using pre-built system prompt
        ContextBudget budget = calculateBudget(tools, systemPrompt);

        // Get messages from session
        List<Message> sessionMessages = new ArrayList<>(session.messages());

        // Apply sliding window
        List<Message> windowedMessages = applyWindow(sessionMessages);

        // Add new prompt if provided
        if (newPrompt != null && !newPrompt.isEmpty()) {
            windowedMessages.add(Message.user(newPrompt));
        }

        // Estimate current tokens
        int estimated = estimateTokens(windowedMessages);

        // Check if compression is needed
        int threshold = (int) (budget.availableForInput() * config.compressionThreshold());
        boolean compressionNeeded = estimated > threshold;
        CompressionResult compressionResult = null;

        if (compressionNeeded && compressor != null) {
            logger.info("Context compression needed: {} tokens > {} threshold",
                estimated, threshold);

            // Perform compression
            int targetTokens = (int) (budget.availableForInput() * 0.7);  // Aim for 70% utilization
            compressionResult = compressor.compress(windowedMessages, targetTokens);

            // Use compressed messages
            windowedMessages = new ArrayList<>(compressionResult.compressedMessages());
            estimated = compressionResult.tokensAfter();

            // If compression generated a summary, prepend it to system prompt
            // This ensures system message stays first (required by chat templates)
            if (compressionResult.summary() != null && !compressionResult.summary().isEmpty()) {
                systemPrompt = systemPrompt + "\n\n[Previous conversation summary]\n" + compressionResult.summary();
            }

            logger.info("Compression complete: {} -> {} tokens (saved {})",
                compressionResult.tokensBefore(), compressionResult.tokensAfter(),
                compressionResult.compressionSaved());
        }

        return new BuiltContext(
            windowedMessages,
            systemPrompt,
            estimated,
            budget,
            compressionNeeded,
            compressionResult
        );
    }

    /**
     * Get the system prompt, using dynamic builder if available.
     */
    private String getSystemPrompt() {
        if (promptBuilder != null) {
            return promptBuilder.build();
        }
        return config.systemPrompt() != null ? config.systemPrompt() : "";
    }

    /**
     * Calculate token budget allocation.
     *
     * @param tools          Available tools for budget estimation
     * @param systemPrompt   Pre-built system prompt (avoid duplicate build() calls)
     */
    private ContextBudget calculateBudget(List<Object> tools, String systemPrompt) {
        // Use provided systemPrompt to avoid duplicate build() calls
        if (systemPrompt == null) {
            systemPrompt = getSystemPrompt();
        }
        int systemTokens = tokenCounter.count(systemPrompt);
        int toolTokens = estimateToolOverhead(tools);

        return ContextBudget.allocate(
            config.maxTokens(),
            systemTokens,
            toolTokens
        );
    }

    /**
     * Estimate token overhead for tool definitions.
     *
     * Each tool definition adds overhead for:
     * - Tool name and description
     * - Input schema (JSON)
     * - Format overhead
     *
     * @param tools List of tools (can be Tool objects or ToolDefinition objects)
     * @return Estimated token overhead
     */
    private int estimateToolOverhead(List<Object> tools) {
        if (tools == null || tools.isEmpty()) {
            return 0;
        }

        int overhead = 0;
        for (Object tool : tools) {
            // Base overhead per tool: ~50 tokens for name, description, format
            overhead += 50;

            // If it's a Tool, estimate schema overhead
            if (tool instanceof com.harness.core.Tool) {
                com.harness.core.Tool t = (com.harness.core.Tool) tool;
                if (t.inputSchema() != null) {
                    // Rough estimate: JSON schema adds ~100-200 tokens
                    overhead += 150;
                }
            }
        }

        return overhead;
    }

    /**
     * Apply sliding window to messages.
     *
     * @param messages All messages
     * @return Messages within window size
     */
    private List<Message> applyWindow(List<Message> messages) {
        if (messages.size() <= config.windowSize()) {
            return messages;
        }
        return new ArrayList<>(messages.subList(messages.size() - config.windowSize(), messages.size()));
    }

    /**
     * Estimate total tokens in messages.
     *
     * @param messages Messages to estimate
     * @return Estimated token count
     */
    private int estimateTokens(List<Message> messages) {
        int total = 0;
        for (Message msg : messages) {
            String content = msg.contentAsString();
            total += tokenCounter.count(content);
            total += 4;  // Message format overhead
        }
        return total;
    }

    /**
     * Build message list within token budget.
     *
     * Uses sliding window to fit messages within budget.
     *
     * @param session      Current session
     * @param newPrompt    Optional new user prompt
     * @param tokenBudget  Maximum tokens for messages
     * @return List of messages in API format
     */
    private List<Message> buildMessages(Session session, String newPrompt, int tokenBudget) {
        List<Message> messages = new ArrayList<>();

        // Start with window size limit
        int windowSize = config.windowSize();
        List<Message> recent = session.messages().size() > windowSize
            ? new ArrayList<>(session.messages().subList(session.messages().size() - windowSize, session.messages().size()))
            : new ArrayList<>(session.messages());

        // Add messages from newest to oldest until budget exhausted
        int currentTokens = 0;
        List<Message> includedMessages = new ArrayList<>();

        for (int i = recent.size() - 1; i >= 0; i--) {
            Message msg = recent.get(i);
            int msgTokens = tokenCounter.count(msg.contentAsString());

            if (currentTokens + msgTokens <= tokenBudget) {
                includedMessages.add(0, msg);
                currentTokens += msgTokens;
            } else {
                // Budget exhausted, stop adding older messages
                break;
            }
        }

        messages.addAll(includedMessages);

        // Add new prompt if provided
        if (newPrompt != null && !newPrompt.isEmpty()) {
            messages.add(Message.user(newPrompt));
        }

        return messages;
    }

    /**
     * Get messages that fit within token budget.
     *
     * @param session    Current session
     * @param maxTokens  Maximum tokens for messages
     * @return List of messages fitting within budget
     */
    public List<Message> getMessageWindow(Session session, int maxTokens) {
        List<Message> messages = new ArrayList<>();
        int currentTokens = 0;

        for (int i = session.messages().size() - 1; i >= 0; i--) {
            Message msg = session.messages().get(i);
            int msgTokens = tokenCounter.count(msg.contentAsString());

            if (currentTokens + msgTokens <= maxTokens) {
                messages.add(0, msg);
                currentTokens += msgTokens;
            } else {
                break;
            }
        }

        return messages;
    }

    // Configuration methods (mutate config and re-initialize if needed)

    /**
     * Set the maximum context window tokens.
     */
    public ContextBuilder withMaxTokens(int maxTokens) {
        this.config.setMaxTokens(maxTokens);
        return this;
    }

    /**
     * Set the base system prompt.
     */
    public ContextBuilder withSystemPrompt(String systemPrompt) {
        this.config.setSystemPrompt(systemPrompt);
        // Update prompt builder if exists
        if (promptBuilder != null) {
            // Update base prompt in config by recreating builder
            initSystemPromptBuilder();
        }
        return this;
    }

    /**
     * Set the message window size.
     */
    public ContextBuilder withWindowSize(int windowSize) {
        this.config.setWindowSize(windowSize);
        return this;
    }

    /**
     * Enable or disable compression.
     */
    public ContextBuilder withCompressionEnabled(boolean enabled) {
        this.config.setEnableCompression(enabled);
        initCompressor();
        return this;
    }

    /**
     * Set the project root for AGENTS.md / MEMORY.md discovery.
     */
    public ContextBuilder withProjectRoot(Path projectRoot) {
        this.config.setProjectRoot(projectRoot);
        // Re-initialize prompt builder with new project root
        initSystemPromptBuilder();
        return this;
    }

    /**
     * Set the path to global MEMORY.md file.
     */
    public ContextBuilder withMemoryMdPath(Path memoryMdPath) {
        this.config.setMemoryMdPath(memoryMdPath);
        // Re-initialize prompt builder with new memory path
        initSystemPromptBuilder();
        return this;
    }

    /**
     * Set the system prompt directly.
     *
     * @param prompt The system prompt to use
     */
    public void setSystemPrompt(String prompt) {
        this.config.setSystemPrompt(prompt);
        // Update prompt builder if exists
        if (promptBuilder != null) {
            // Update base prompt in config by recreating the builder
            initSystemPromptBuilder();
        }
    }

    /**
     * Set the project root for AGENTS.md / MEMORY.md discovery.
     *
     * @param projectRoot Path to project root directory
     */
    public void setProjectRoot(Path projectRoot) {
        this.config.setProjectRoot(projectRoot);
        // Re-initialize prompt builder with new project root
        initSystemPromptBuilder();
    }

    /**
     * Add a custom system prompt source.
     *
     * @param source SystemPromptSource to add
     */
    public void addPromptSource(SystemPromptSource source) {
        if (promptBuilder == null) {
            // Initialize builder if not exists
            initSystemPromptBuilder();
        }
        if (promptBuilder != null) {
            promptBuilder.addSource(source);
        }
    }

    /**
     * Get list of prompt sources that have content.
     *
     * @return List of available source names
     */
    public List<String> getAvailablePromptSources() {
        if (promptBuilder != null) {
            return promptBuilder.getAvailableSources();
        }
        List<String> result = new ArrayList<>();
        if (config.systemPrompt() != null && !config.systemPrompt().isEmpty()) {
            result.add("base");
        }
        return result;
    }

    /**
     * Estimate token count for content using tiktoken.
     *
     * @param content Content to estimate
     * @return Estimated token count
     */
    public int estimateTokens(String content) {
        return tokenCounter.count(content);
    }
}