package com.harness.integration;

import java.nio.file.Path;
import java.util.*;
import java.util.concurrent.CompletableFuture;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.llm.AnthropicClient;
import com.harness.llm.LLMClient;
import com.harness.llm.OpenAIClient;
import com.harness.memory.SessionManager;
import com.harness.memory.SystemPromptBuilder;
import com.harness.memory.SystemPromptConfig;
import com.harness.skills.SkillInjector;
import com.harness.skills.SkillLoader;
import com.harness.skills.SkillRegistry;
import com.harness.types.*;

/**
 * The main Harness SDK class.
 *
 * This class provides a simple interface to create and run AI agents
 * that can use tools, maintain memory, and execute complex tasks.
 *
 * Example with Anthropic:
 * <pre>
 * AgentHarness agent = AgentHarness.builder()
 *     .model("claude-sonnet-4-6")
 *     .tools(Arrays.asList(new ReadTool()))
 *     .build();
 *
 * LoopResult result = agent.run("Read the main.py file").join();
 * System.out.println(result.content());
 * </pre>
 *
 * Example with OpenAI:
 * <pre>
 * AgentHarness agent = AgentHarness.builder()
 *     .model("gpt-4o")
 *     .provider("openai")
 *     .build();
 * </pre>
 *
 * Example with custom LLM:
 * <pre>
 * AgentHarness agent = AgentHarness.builder()
 *     .llmClient(new MyCustomLLMClient())
 *     .build();
 * </pre>
 */
public class AgentHarness {

    private static final Logger logger = LoggerFactory.getLogger(AgentHarness.class);

    private final HarnessConfig config;
    private final LLMClient llm;
    private final ToolRegistry toolRegistry;
    private final ToolExecutor toolExecutor;
    private final SessionManager sessionManager;
    private final SystemPromptBuilder systemPromptBuilder;
    private final AgentLoop loop;
    private final SkillRegistry skillRegistry;
    private final SkillLoader skillLoader;
    private final SkillInjector skillInjector;

    private AgentHarness(Builder builder) {
        // Merge config
        if (builder.config != null) {
            this.config = builder.config;
        } else {
            HarnessConfig.HarnessConfig.Builder configBuilder = HarnessConfig.builder()
                .model(builder.model)
                .provider(builder.provider)
                .maxIterations(builder.maxIterations);

            if (builder.apiKey != null) {
                configBuilder.apiKey(builder.apiKey);
            }
            if (builder.baseUrl != null) {
                configBuilder.baseUrl(builder.baseUrl);
            }

            this.config = configBuilder.build();
        }

        // Initialize LLM client
        if (builder.llmClient != null) {
            this.llm = builder.llmClient;
        } else {
            this.llm = createLLMClient();
        }

        // Initialize tool registry
        this.toolRegistry = new ToolRegistry();
        if (builder.tools != null) {
            for (Tool tool : builder.tools) {
                toolRegistry.register(tool);
            }
        }

        // Initialize tool executor
        this.toolExecutor = new ToolExecutor(toolRegistry);

        // Initialize session manager
        this.sessionManager = new SessionManager();

        // Initialize system prompt builder
        this.systemPromptBuilder = new SystemPromptBuilder(
            SystemPromptConfig.builder()
                .systemPrompt(config.getSystemPrompt())
                .build()
        );

        // Initialize agent loop
        LoopConfig loopConfig = LoopConfig.builder()
            .maxIterations(config.getMaxIterations())
            .timeoutPerTool(config.getToolTimeout())
            .build();

        this.loop = new AgentLoop(llm, toolExecutor, sessionManager, loopConfig);

        // Initialize skill system
        this.skillRegistry = new SkillRegistry();
        this.skillLoader = new SkillLoader(skillRegistry);
        this.skillInjector = new SkillInjector(skillRegistry);

        logger.info("AgentHarness initialized with model: {}", config.getModel());
    }

    /**
     * Create LLM client based on config.
     */
    private LLMClient createLLMClient() {
        String provider = config.getProvider();
        String model = config.getModel();

        // Auto-detect provider from model name
        if ("auto".equals(provider)) {
            if (model.startsWith("claude")) {
                provider = "anthropic";
            } else {
                provider = "openai";
            }
        }

        if ("anthropic".equals(provider)) {
            return new AnthropicClient(
                config.getApiKey(),
                model,
                config.getMaxTokens()
            );
        } else {
            return new OpenAIClient(
                config.getApiKey(),
                model,
                config.getBaseUrl(),
                config.getMaxTokens()
            );
        }
    }

    /**
     * Run the agent with a prompt.
     *
     * @param prompt User input
     * @return CompletableFuture with result
     */
    public CompletableFuture<LoopResult> run(String prompt) {
        return run(prompt, null, null);
    }

    /**
     * Run the agent with a prompt and session.
     *
     * @param prompt User input
     * @param sessionId Optional session ID for conversation continuity
     * @return CompletableFuture with result
     */
    public CompletableFuture<LoopResult> run(String prompt, String sessionId) {
        return run(prompt, sessionId, null);
    }

    /**
     * Run the agent with a prompt, session, and progress callback.
     *
     * @param prompt User input
     * @param sessionId Optional session ID for conversation continuity
     * @param onProgress Optional callback for progress events
     * @return CompletableFuture with result
     */
    public CompletableFuture<LoopResult> run(String prompt, String sessionId, java.util.function.Consumer<ProgressEvent> onProgress) {
        // Get or create session
        Session session = sessionManager.getOrCreate(sessionId);

        // Inject matching skills into system prompt
        String enhancedSystemPrompt = skillInjector.injectSkills(config.getSystemPrompt(), prompt);

        // Build context
        List<Message> messages = new ArrayList<>(session.messages());
        messages.add(new Message("user", prompt, null));

        // Get tool definitions
        List<Map<String, Object>> toolDefs = toolRegistry.getDefinitions();

        // Run the loop
        return loop.run(prompt, session, toolDefs.isEmpty() ? null : toolDefs, onProgress)
            .thenApply(result -> {
                // Save session
                sessionManager.updateSession(result.session());
                return result;
            });
    }

    /**
     * Stream the agent's response.
     *
     * @param prompt User input
     * @param sessionId Optional session ID
     * @param onChunk Callback for each text chunk
     * @return CompletableFuture with result
     */
    public CompletableFuture<LoopResult> stream(
        String prompt,
        String sessionId,
        java.util.function.Consumer<String> onChunk
    ) {
        return run(prompt, sessionId).thenApply(result -> {
            if (onChunk != null && result.content() != null) {
                // Simulate streaming by yielding chunks
                String content = result.content();
                int chunkSize = Math.max(1, content.length() / 50);
                for (int i = 0; i < content.length(); i += chunkSize) {
                    int end = Math.min(i + chunkSize, content.length());
                    onChunk.accept(content.substring(i, end));
                }
            }
            return result;
        });
    }

    /**
     * Register a tool with the agent.
     *
     * @param tool Tool instance to register
     * @param category Category for organization
     */
    public void registerTool(Tool tool, String category) {
        toolRegistry.register(tool, category);
    }

    /**
     * Register a tool with default category.
     */
    public void registerTool(Tool tool) {
        toolRegistry.register(tool);
    }

    /**
     * Get an existing session.
     */
    public Session getSession(String sessionId) {
        return sessionManager.getSession(sessionId);
    }

    /**
     * Clear a session's messages.
     */
    public void clearSession(String sessionId) {
        sessionManager.clearSession(sessionId);
    }

    /**
     * Interrupt the current execution.
     */
    public void interrupt() {
        loop.interrupt();
    }

    /**
     * Add a lifecycle hook.
     *
     * @param hook The hook to register
     */
    public void addHook(LifecycleHook hook) {
        loop.addHook(hook);
    }

    /**
     * Remove a lifecycle hook.
     *
     * @param hook The hook to unregister
     */
    public void removeHook(LifecycleHook hook) {
        loop.removeHook(hook);
    }

    /**
     * Load skills from a directory.
     *
     * @param directory Directory containing skill files
     * @return Number of skills loaded
     */
    public int loadSkillsFromDir(Path directory) {
        return skillLoader.loadFromDir(directory);
    }

    /**
     * Activate a skill by name.
     */
    public boolean activateSkill(String skillName) {
        return skillRegistry.activate(skillName);
    }

    /**
     * Deactivate a skill by name.
     */
    public boolean deactivateSkill(String skillName) {
        return skillRegistry.deactivate(skillName);
    }

    /**
     * Get the tool registry.
     */
    public ToolRegistry getToolRegistry() {
        return toolRegistry;
    }

    /**
     * Get the configuration.
     */
    public HarnessConfig getConfig() {
        return config;
    }

    /**
     * Create builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    /**
     * Builder for AgentHarness.
     */
    public static class Builder {
        private String model = "claude-sonnet-4-6";
        private String apiKey = null;
        private String provider = "anthropic";
        private String baseUrl = null;
        private List<Tool> tools = null;
        private HarnessConfig config = null;
        private LLMClient llmClient = null;
        private int maxIterations = 10;

        public Builder model(String model) {
            this.model = model;
            return this;
        }

        public Builder apiKey(String apiKey) {
            this.apiKey = apiKey;
            return this;
        }

        public Builder provider(String provider) {
            this.provider = provider;
            return this;
        }

        public Builder baseUrl(String baseUrl) {
            this.baseUrl = baseUrl;
            return this;
        }

        public Builder tools(List<Tool> tools) {
            this.tools = tools;
            return this;
        }

        public Builder config(HarnessConfig config) {
            this.config = config;
            return this;
        }

        public Builder llmClient(LLMClient llmClient) {
            this.llmClient = llmClient;
            return this;
        }

        public Builder maxIterations(int maxIterations) {
            this.maxIterations = maxIterations;
            return this;
        }

        public AgentHarness build() {
            return new AgentHarness(this);
        }
    }

    /**
     * Create agent from environment variables.
     */
    public static AgentHarness fromEnv() {
        return builder()
            .config(HarnessConfig.fromEnv())
            .build();
    }
}
