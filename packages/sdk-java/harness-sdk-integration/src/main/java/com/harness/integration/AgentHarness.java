package com.harness.integration;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Consumer;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.core.HarnessConfig;
import com.harness.core.LLMClient;
import com.harness.core.LoopConfig;
import com.harness.core.Tool;
import com.harness.core.ToolRegistry;
import com.harness.core.LifecycleHook;
import com.harness.skills.SkillInjector;
import com.harness.skills.SkillLoader;
import com.harness.skills.SkillRegistry;
import com.harness.types.LoopResult;
import com.harness.types.Session;
import com.harness.types.TokenUsage;

/**
 * The main Harness SDK class.
 *
 * This class provides a simple interface to create and run AI agents
 * that can use tools, maintain memory, and execute complex tasks.
 *
 * Features:
 * - Tool registration and management
 * - Lifecycle hooks for extensibility
 * - Session management
 * - Integration with AgentLoop for ReAct execution
 *
 * Example:
 * <pre>
 * AgentHarness agent = AgentHarness.builder()
 *     .model("claude-sonnet-4-6")
 *     .llmClient(myClient)
 *     .addTool(new ReadTool())
 *     .addTool(new WriteTool())
 *     .build();
 *
 * agent.addHook(new LoggingHook());
 *
 * LoopResult result = agent.run("Read the file and summarize it").join();
 * </pre>
 */
public class AgentHarness {

    private static final Logger logger = LoggerFactory.getLogger(AgentHarness.class);

    private final HarnessConfig config;
    private final LLMClient llmClient;
    private final ToolRegistry toolRegistry;
    private final List<Tool> toolsList = new ArrayList<>();
    private final HookRegistry hookRegistry;
    private final AgentLoop agentLoop;

    // Session management
    private final Map<String, Session> sessions = new ConcurrentHashMap<>();

    // Skill system
    private final SkillRegistry skillRegistry;
    private final SkillLoader skillLoader;
    private final SkillInjector skillInjector;

    /**
     * Create AgentHarness with configuration.
     */
    public AgentHarness(HarnessConfig config) {
        this.config = config;
        this.toolRegistry = new ToolRegistry();
        this.llmClient = null; // Will be set via builder or method
        this.hookRegistry = new HookRegistry();
        this.agentLoop = null;

        // Initialize skill system
        this.skillRegistry = new SkillRegistry();
        this.skillLoader = new SkillLoader(skillRegistry);
        this.skillInjector = new SkillInjector(skillRegistry);
        this.skillLoader.loadDefaults();

        logger.info("AgentHarness initialized with model: {}", config.getModel());
    }

    /**
     * Create AgentHarness with LLM client directly.
     */
    public AgentHarness(LLMClient llmClient, HarnessConfig config) {
        this.config = config;
        this.llmClient = llmClient;
        this.toolRegistry = new ToolRegistry();
        this.hookRegistry = new HookRegistry();

        // Initialize skill system
        this.skillRegistry = new SkillRegistry();
        this.skillLoader = new SkillLoader(skillRegistry);
        this.skillInjector = new SkillInjector(skillRegistry);
        this.skillLoader.loadDefaults();

        // Create loop config from harness config
        LoopConfig loopConfig = LoopConfig.builder()
            .maxIterations(config.getMaxIterations())
            .timeoutPerTool((long) (config.getToolTimeout() * 1000))
            .workingDirectory(config.getSandboxWorkspace() != null
                ? config.getSandboxWorkspace()
                : System.getProperty("user.dir"))
            .build();

        this.agentLoop = new AgentLoop(llmClient, toolsList, loopConfig, hookRegistry);
        logger.info("AgentHarness initialized with custom LLM client and AgentLoop");
    }

    /**
     * Create AgentHarness with LLM client and tools.
     */
    public AgentHarness(LLMClient llmClient, HarnessConfig config, List<Tool> tools) {
        this(llmClient, config);
        for (Tool tool : tools) {
            registerTool(tool);
        }
    }

    /**
     * Run agent with a prompt.
     *
     * @param prompt User prompt
     * @return LoopResult
     */
    public CompletableFuture<LoopResult> run(String prompt) {
        return run(prompt, null, null);
    }

    /**
     * Run agent with a prompt and session ID.
     *
     * @param prompt User prompt
     * @param sessionId Optional session ID
     * @return LoopResult
     */
    public CompletableFuture<LoopResult> run(String prompt, String sessionId) {
        return run(prompt, sessionId, null);
    }

    /**
     * Run agent with a prompt, session ID, and progress callback.
     *
     * @param prompt User prompt
     * @param sessionId Optional session ID
     * @param onProgress Optional progress callback
     * @return LoopResult
     */
    public CompletableFuture<LoopResult> run(String prompt, String sessionId, Consumer<Object> onProgress) {
        logger.info("Running agent with prompt: {}...", prompt.substring(0, Math.min(50, prompt.length())));

        if (agentLoop == null) {
            logger.warn("No LLM client configured, returning placeholder result");
            Session session = Session.create(sessionId != null ? sessionId : "default");
            return CompletableFuture.completedFuture(
                LoopResult.completed(
                    session,
                    "Agent response placeholder",
                    1,
                    new TokenUsage(100, 50)
                )
            );
        }

        // Get or create session
        String effectiveSessionId = sessionId != null ? sessionId : generateSessionId();
        Session session = getOrCreateSession(effectiveSessionId);

        // Add user message to session
        session = session.addMessage(com.harness.types.Message.user(prompt));
        sessions.put(effectiveSessionId, session);

        // Run agent loop
        return agentLoop.run(session, onProgress)
            .thenApply(result -> {
                // Update session in map
                sessions.put(effectiveSessionId, result.session());
                return result;
            });
    }

    /**
     * Continue an existing session.
     *
     * @param sessionId Session ID
     * @param prompt Additional prompt
     * @return LoopResult
     */
    public CompletableFuture<LoopResult> continueSession(String sessionId, String prompt) {
        return continueSession(sessionId, prompt, null);
    }

    /**
     * Continue an existing session with progress callback.
     *
     * @param sessionId Session ID
     * @param prompt Additional prompt
     * @param onProgress Optional progress callback
     * @return LoopResult
     */
    public CompletableFuture<LoopResult> continueSession(String sessionId, String prompt, Consumer<Object> onProgress) {
        Session session = sessions.get(sessionId);
        if (session == null) {
            logger.warn("Session {} not found, creating new", sessionId);
            session = Session.create(sessionId);
        }

        // Add user message to session
        session = session.addMessage(com.harness.types.Message.user(prompt));
        sessions.put(sessionId, session);

        if (agentLoop == null) {
            return CompletableFuture.completedFuture(
                LoopResult.completed(session, "Placeholder", 1, new TokenUsage(0, 0))
            );
        }

        return agentLoop.run(session, onProgress)
            .thenApply(result -> {
                sessions.put(sessionId, result.session());
                return result;
            });
    }

    /**
     * Register a tool.
     */
    public void registerTool(Tool tool) {
        toolRegistry.register(tool);
        toolsList.add(tool);
        logger.debug("Registered tool: {}", tool.name());
    }

    /**
     * Register a tool with category.
     */
    public void registerTool(Tool tool, String category) {
        toolRegistry.register(tool, category);
        toolsList.add(tool);
        logger.debug("Registered tool {} in category {}", tool.name(), category);
    }

    /**
     * Register multiple tools.
     */
    public void registerTools(List<Tool> tools) {
        for (Tool tool : tools) {
            registerTool(tool);
        }
    }

    /**
     * Add a lifecycle hook.
     */
    public void addHook(LifecycleHook hook) {
        hookRegistry.register(hook);
        logger.debug("Registered hook: {}", hook.getClass().getSimpleName());
    }

    /**
     * Remove a lifecycle hook.
     */
    public void removeHook(LifecycleHook hook) {
        hookRegistry.unregister(hook);
        logger.debug("Removed hook: {}", hook.getClass().getSimpleName());
    }

    /**
     * Clear all hooks.
     */
    public void clearHooks() {
        hookRegistry.clear();
    }

    /**
     * Get tool registry.
     */
    public ToolRegistry getToolRegistry() {
        return toolRegistry;
    }

    /**
     * Get configuration.
     */
    public HarnessConfig getConfig() {
        return config;
    }

    /**
     * Get hook registry.
     */
    public HookRegistry getHookRegistry() {
        return hookRegistry;
    }

    /**
     * Get or create session.
     */
    public Session getOrCreateSession(String sessionId) {
        return sessions.computeIfAbsent(sessionId, Session::create);
    }

    /**
     * Get session.
     */
    public Session getSession(String sessionId) {
        return sessions.get(sessionId);
    }

    /**
     * Get all sessions.
     */
    public Map<String, Session> getAllSessions() {
        return new ConcurrentHashMap<>(sessions);
    }

    /**
     * Clear a session.
     */
    public void clearSession(String sessionId) {
        sessions.remove(sessionId);
        hookRegistry.resetSession(sessionId);
    }

    /**
     * Clear all sessions.
     */
    public void clearAllSessions() {
        sessions.clear();
        hookRegistry.reset();
    }

    /**
     * Get agent loop statistics.
     */
    public Map<String, Object> getStats() {
        Map<String, Object> stats = new java.util.HashMap<>();
        stats.put("sessionCount", sessions.size());
        stats.put("toolCount", toolsList.size());
        stats.put("hookCount", hookRegistry.getAllHooks().size());
        if (agentLoop != null) {
            stats.put("circuitBreaker", agentLoop.getCircuitBreakerStats());
            stats.put("budget", agentLoop.getBudgetStats());
        }
        return stats;
    }

    /**
     * Reset agent state.
     */
    public void reset() {
        if (agentLoop != null) {
            agentLoop.reset();
        }
        hookRegistry.reset();
    }

    // -------------------------------------------------------------------------
    // Skill System Methods
    // -------------------------------------------------------------------------

    /**
     * Get the skill registry.
     */
    public SkillRegistry getSkillRegistry() {
        return skillRegistry;
    }

    /**
     * Get the skill loader.
     */
    public SkillLoader getSkillLoader() {
        return skillLoader;
    }

    /**
     * Get the skill injector.
     */
    public SkillInjector getSkillInjector() {
        return skillInjector;
    }

    /**
     * Reload skills from disk.
     */
    public void reloadSkills() {
        skillRegistry.reload();
        skillLoader.loadDefaults();
        logger.info("Skills reloaded");
    }

    /**
     * Inject skills into a system prompt.
     *
     * @param systemPrompt Original system prompt
     * @param userInput User's input text
     * @return Enhanced system prompt with skills injected
     */
    public String injectSkills(String systemPrompt, String userInput) {
        return skillInjector.injectSkills(systemPrompt, userInput);
    }

    /**
     * List all available skills.
     */
    public java.util.List<String> listSkills() {
        return skillRegistry.listSkills();
    }

    /**
     * Generate unique session ID.
     */
    private String generateSessionId() {
        return "session_" + java.util.UUID.randomUUID().toString().substring(0, 8);
    }

    /**
     * Builder for AgentHarness.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private HarnessConfig config = HarnessConfig.defaults();
        private LLMClient llmClient = null;
        private final List<Tool> tools = new ArrayList<>();
        private final List<LifecycleHook> hooks = new ArrayList<>();

        public Builder config(HarnessConfig config) {
            this.config = config;
            return this;
        }

        public Builder model(String model) {
            this.config = HarnessConfig.builder().model(model).build();
            return this;
        }

        public Builder apiKey(String apiKey) {
            this.config = HarnessConfig.builder()
                .model(config.getModel())
                .apiKey(apiKey)
                .build();
            return this;
        }

        public Builder llmClient(LLMClient llmClient) {
            this.llmClient = llmClient;
            return this;
        }

        public Builder tools(List<Tool> tools) {
            this.tools.addAll(tools);
            return this;
        }

        public Builder addTool(Tool tool) {
            this.tools.add(tool);
            return this;
        }

        public Builder hooks(List<LifecycleHook> hooks) {
            this.hooks.addAll(hooks);
            return this;
        }

        public Builder addHook(LifecycleHook hook) {
            this.hooks.add(hook);
            return this;
        }

        public AgentHarness build() {
            AgentHarness harness = llmClient != null
                ? new AgentHarness(llmClient, config, tools)
                : new AgentHarness(config);

            // Register any hooks added via builder
            for (LifecycleHook hook : hooks) {
                harness.addHook(hook);
            }

            return harness;
        }
    }
}