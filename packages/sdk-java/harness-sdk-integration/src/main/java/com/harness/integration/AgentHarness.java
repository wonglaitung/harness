package com.harness.integration;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
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
import com.harness.loop.GoalLoop;
import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.VerificationMethod;
import com.harness.skills.Skill;
import com.harness.skills.SkillInjector;
import com.harness.skills.SkillLoader;
import com.harness.skills.ProgressiveSkillLoader;
import com.harness.skills.SkillRegistry;
import com.harness.mcp.McpManager;
import com.harness.mcp.McpServerConfig;
import com.harness.mcp.McpToolInfo;
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
    private final ProgressiveSkillLoader progressiveLoader;
    private final List<ProgressiveSkillLoader.SkillMetadata> skillMetadata = new ArrayList<>();
    private final Map<String, ProgressiveSkillLoader.SkillMetadata> skillMetadataByName = new ConcurrentHashMap<>();
    private final Set<String> activatedSkills = ConcurrentHashMap.newKeySet();
    private final SkillInjector skillInjector;

    // MCP system
    private final McpManager mcpManager;

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
        this.progressiveLoader = new ProgressiveSkillLoader();
        this.skillInjector = new SkillInjector(skillRegistry);
        this.skillLoader.loadDefaults();
        loadSkillMetadata();  // Level 1: Load metadata only

        // Initialize MCP manager
        this.mcpManager = new McpManager();

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
        this.progressiveLoader = new ProgressiveSkillLoader();
        this.skillInjector = new SkillInjector(skillRegistry);
        this.skillLoader.loadDefaults();
        loadSkillMetadata();  // Level 1: Load metadata only

        // Create loop config from harness config
        LoopConfig loopConfig = LoopConfig.builder()
            .maxIterations(config.getMaxIterations())
            .timeoutPerTool((long) (config.getToolTimeout() * 1000))
            .workingDirectory(config.getSandboxWorkspace() != null
                ? config.getSandboxWorkspace()
                : System.getProperty("user.dir"))
            .memoryMdPath(config.getMemoryMdPath())
            .toolResultRole(config.getToolResultRole())
            .build();

        this.agentLoop = new AgentLoop(llmClient, toolsList, loopConfig, hookRegistry);

        // Initialize MCP manager
        this.mcpManager = new McpManager();

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

        // Level 2: Load full content for matching and activated skills
        List<ProgressiveSkillLoader.SkillMetadata> matchedMetadata = progressiveLoader.matchSkills(prompt, skillMetadata);

        // Combine matched skills with explicitly activated skills
        Set<String> skillsToLoad = new java.util.HashSet<>();
        for (ProgressiveSkillLoader.SkillMetadata meta : matchedMetadata) {
            skillsToLoad.add(meta.name());
        }
        skillsToLoad.addAll(activatedSkills);

        // Load full content for skills not yet loaded
        for (ProgressiveSkillLoader.SkillMetadata meta : skillMetadata) {
            if (skillsToLoad.contains(meta.name()) && skillRegistry.getSkill(meta.name()).isEmpty()) {
                Skill skill = progressiveLoader.loadFullContent(meta);
                if (skill != null) {
                    skillRegistry.registerSkill(skill);
                }
            }
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
     * Run the agent in goal-driven mode.
     *
     * <p>The agent will continue execution until the goal is achieved
     * or a limit is reached (iterations, timeout, cost).</p>
     *
     * @param goal Description of the goal to achieve
     * @return GoalResult with achievement status and execution details
     */
    public CompletableFuture<GoalResult> runGoal(String goal) {
        return runGoal(goal, null, null, null);
    }

    /**
     * Run the agent in goal-driven mode with session ID.
     *
     * @param goal Description of the goal to achieve
     * @param sessionId Optional session ID for conversation continuity
     * @return GoalResult with achievement status and execution details
     */
    public CompletableFuture<GoalResult> runGoal(String goal, String sessionId) {
        return runGoal(goal, sessionId, null, null);
    }

    /**
     * Run the agent in goal-driven mode with session ID and progress callback.
     *
     * @param goal Description of the goal to achieve
     * @param sessionId Optional session ID for conversation continuity
     * @param onProgress Optional progress callback
     * @param customVerifier Optional custom verification function
     * @return GoalResult with achievement status and execution details
     */
    public CompletableFuture<GoalResult> runGoal(
            String goal,
            String sessionId,
            Consumer<Object> onProgress,
            java.util.function.Function<GoalResult, Boolean> customVerifier) {
        logger.info("Running goal: {}...", goal.substring(0, Math.min(50, goal.length())));

        VerificationMethod verificationMethod = customVerifier != null
                ? VerificationMethod.CUSTOM
                : VerificationMethod.LLM;

        GoalConfig config = GoalConfig.builder()
                .description(goal)
                .sessionId(sessionId)
                .verificationMethod(verificationMethod)
                .customVerifier(customVerifier)
                .build();

        GoalLoop loop = new GoalLoop(new GoalLoop.AgentRunner() {
            @Override
            public CompletableFuture<LoopResult> run(String prompt, String sid) {
                return AgentHarness.this.run(prompt, sid);
            }

            @Override
            public CompletableFuture<LoopResult> run(String prompt, String sid, Consumer<Object> progress) {
                return AgentHarness.this.run(prompt, sid, progress);
            }

            @Override
            public Session getSession(String sid) {
                return AgentHarness.this.getSession(sid);
            }

            @Override
            public int getContextWindow() {
                return AgentHarness.this.config.getContextWindow();
            }
        }, config, onProgress);

        return loop.run();
    }

    /**
     * Run the agent in goal-driven mode with full configuration.
     *
     * @param goalConfig Complete goal configuration
     * @param onProgress Optional progress callback
     * @return GoalResult with achievement status and execution details
     */
    public CompletableFuture<GoalResult> runGoal(GoalConfig goalConfig, Consumer<Object> onProgress) {
        logger.info("Running goal: {}...", goalConfig.getDescription().substring(0, Math.min(50, goalConfig.getDescription().length())));

        GoalLoop loop = new GoalLoop(new GoalLoop.AgentRunner() {
            @Override
            public CompletableFuture<LoopResult> run(String prompt, String sessionId) {
                return AgentHarness.this.run(prompt, sessionId);
            }

            @Override
            public CompletableFuture<LoopResult> run(String prompt, String sessionId, Consumer<Object> progress) {
                return AgentHarness.this.run(prompt, sessionId, progress);
            }

            @Override
            public Session getSession(String sessionId) {
                return AgentHarness.this.getSession(sessionId);
            }

            @Override
            public int getContextWindow() {
                return AgentHarness.this.config.getContextWindow();
            }
        }, goalConfig, onProgress);

        return loop.run();
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
     * Get LLM client.
     */
    public LLMClient getLLMClient() {
        return llmClient;
    }

    /**
     * Get all registered tools.
     */
    public List<Tool> getAllTools() {
        return new ArrayList<>(toolsList);
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
     * Load skill metadata from default directories (Level 1).
     */
    private void loadSkillMetadata() {
        for (java.nio.file.Path directory : SkillLoader.getDefaultSkillPaths()) {
            if (java.nio.file.Files.exists(directory)) {
                List<ProgressiveSkillLoader.SkillMetadata> skills = progressiveLoader.discoverSkills(directory);
                for (ProgressiveSkillLoader.SkillMetadata meta : skills) {
                    if (!skillMetadataByName.containsKey(meta.name())) {
                        skillMetadata.add(meta);
                        skillMetadataByName.put(meta.name(), meta);
                    }
                }
            }
        }
        logger.debug("Loaded {} skill metadata entries", skillMetadata.size());
    }

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
     * Get the progressive skill loader.
     */
    public ProgressiveSkillLoader getProgressiveLoader() {
        return progressiveLoader;
    }

    /**
     * Get the skill injector.
     */
    public SkillInjector getSkillInjector() {
        return skillInjector;
    }

    /**
     * Load skills from a specific directory using progressive loading.
     *
     * <p>This method discovers skill metadata (frontmatter only) from the given
     * directory. Full skill content is loaded on-demand when:
     * <ul>
     *   <li>The skill is activated via activateSkill()</li>
     *   <li>The skill matches user input during run()</li>
     * </ul>
     *
     * @param directory Path to directory containing skill files
     * @return Number of skills discovered (metadata only)
     */
    public int loadSkillsFromDir(java.nio.file.Path directory) {
        if (!java.nio.file.Files.exists(directory)) {
            logger.warn("Skill directory does not exist: {}", directory);
            return 0;
        }

        // Level 1: Discover metadata only
        List<ProgressiveSkillLoader.SkillMetadata> skills = progressiveLoader.discoverSkills(directory);
        int count = 0;
        for (ProgressiveSkillLoader.SkillMetadata meta : skills) {
            // Skip if already discovered
            if (skillMetadataByName.containsKey(meta.name())) {
                continue;
            }
            skillMetadata.add(meta);
            skillMetadataByName.put(meta.name(), meta);
            count++;
        }

        logger.info("Discovered {} skills from {} (metadata only)", count, directory);
        return count;
    }

    /**
     * Activate a skill by name.
     *
     * <p>This will load the full skill content if not already loaded,
     * then activate it in the registry.
     *
     * @param skillName Name of the skill to activate
     * @return True if activated successfully
     */
    public boolean activateSkill(String skillName) {
        // Track explicitly activated skill
        activatedSkills.add(skillName);

        // Check if skill is already registered with full content
        if (skillRegistry.getSkill(skillName).isPresent()) {
            return skillRegistry.activate(skillName);
        }

        // Find skill metadata and load full content
        ProgressiveSkillLoader.SkillMetadata meta = skillMetadataByName.get(skillName);
        if (meta == null) {
            logger.warn("Skill not found: {}", skillName);
            return false;
        }

        // Level 2: Load full content on activation
        Skill skill = progressiveLoader.loadFullContent(meta);
        if (skill == null) {
            logger.warn("Failed to load skill content: {}", skillName);
            return false;
        }

        // Register and activate
        skillRegistry.registerSkill(skill);
        return skillRegistry.activate(skillName);
    }

    /**
     * Deactivate a skill by name.
     *
     * @param skillName Name of the skill to deactivate
     * @return True if deactivated successfully
     */
    public boolean deactivateSkill(String skillName) {
        activatedSkills.remove(skillName);
        return skillRegistry.deactivate(skillName);
    }

    /**
     * Reload skills from disk.
     */
    public void reloadSkills() {
        skillMetadata.clear();
        skillMetadataByName.clear();
        activatedSkills.clear();
        skillRegistry.reload();
        progressiveLoader.clearCache();
        loadSkillMetadata();
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
     * Get skills that match the user input.
     *
     * @param userInput User's input text
     * @return List of matching skills
     */
    public List<Skill> getMatchingSkills(String userInput) {
        return skillRegistry.findMatchingSkills(userInput);
    }

    /**
     * List all available skills.
     */
    public java.util.List<String> listSkills() {
        return skillRegistry.listSkills();
    }

    /**
     * List all discovered skills (metadata only, Level 1).
     *
     * <p>This returns all skills that have been discovered from skill directories,
     * including those whose full content hasn't been loaded yet.</p>
     *
     * @return List of skill metadata
     */
    public List<ProgressiveSkillLoader.SkillMetadata> listDiscoveredSkills() {
        return new ArrayList<>(skillMetadata);
    }

    /**
     * Get all skills with full content.
     *
     * @return List of all skills
     */
    public List<Skill> getAllSkills() {
        return skillRegistry.getAllSkills();
    }

    /**
     * Get a skill by name.
     *
     * @param name Skill name
     * @return Skill instance or null if not found
     */
    public Skill getSkill(String name) {
        return skillRegistry.getSkill(name).orElse(null);
    }

    // -------------------------------------------------------------------------
    // MCP Methods
    // -------------------------------------------------------------------------

    /**
     * Get the MCP manager.
     */
    public McpManager getMcpManager() {
        return mcpManager;
    }

    /**
     * Add and connect to an MCP server.
     *
     * @param config Server configuration
     * @return true if connected successfully
     */
    public boolean addMcpServer(McpServerConfig config) {
        mcpManager.registerServer(config);
        boolean connected = mcpManager.connect(config.name());
        if (connected) {
            // Register tools from this server
            List<Tool> mcpTools = mcpManager.getHarnessTools(config.name());
            for (Tool tool : mcpTools) {
                registerTool(tool);
            }
            logger.info("MCP server {} connected with {} tools", config.name(), mcpTools.size());
        }
        return connected;
    }

    /**
     * Add an MCP server without connecting.
     *
     * @param config Server configuration
     */
    public void registerMcpServer(McpServerConfig config) {
        mcpManager.registerServer(config);
    }

    /**
     * Connect to a registered MCP server.
     *
     * @param serverName Server name
     * @return true if connected successfully
     */
    public boolean connectMcpServer(String serverName) {
        boolean connected = mcpManager.connect(serverName);
        if (connected) {
            List<Tool> mcpTools = mcpManager.getHarnessTools(serverName);
            for (Tool tool : mcpTools) {
                registerTool(tool);
            }
            logger.info("MCP server {} connected with {} tools", serverName, mcpTools.size());
        }
        return connected;
    }

    /**
     * Connect to all registered MCP servers.
     *
     * @return Map of server name to connection success
     */
    public Map<String, Boolean> connectAllMcpServers() {
        Map<String, Boolean> results = mcpManager.connectAll();
        for (Map.Entry<String, Boolean> entry : results.entrySet()) {
            if (entry.getValue()) {
                List<Tool> mcpTools = mcpManager.getHarnessTools(entry.getKey());
                for (Tool tool : mcpTools) {
                    registerTool(tool);
                }
            }
        }
        return results;
    }

    /**
     * Disconnect from an MCP server.
     *
     * @param serverName Server name
     */
    public void disconnectMcpServer(String serverName) {
        mcpManager.disconnect(serverName);
        logger.info("Disconnected from MCP server: {}", serverName);
    }

    /**
     * Disconnect from all MCP servers.
     */
    public void disconnectAllMcpServers() {
        mcpManager.disconnectAll();
        logger.info("Disconnected from all MCP servers");
    }

    /**
     * List all registered MCP servers.
     */
    public List<String> listMcpServers() {
        return mcpManager.getRegisteredServers();
    }

    /**
     * List connected MCP servers.
     */
    public List<String> listConnectedMcpServers() {
        return mcpManager.getConnectedServers();
    }

    /**
     * Get MCP server status.
     */
    public Map<String, String> getMcpStatus() {
        return mcpManager.getStatus();
    }

    /**
     * Get MCP server configuration by name.
     *
     * @param serverName Server name
     * @return Server configuration or null if not found
     */
    public McpServerConfig getMcpServerConfig(String serverName) {
        return mcpManager.getConfig(serverName);
    }

    /**
     * Get tools from a connected MCP server.
     *
     * @param serverName Server name
     * @return List of MCP tool info
     */
    public List<McpToolInfo> getMcpServerTools(String serverName) {
        return mcpManager.getServerToolInfos(serverName);
    }

    /**
     * Get all tools from all connected MCP servers.
     *
     * @return List of all MCP tool info
     */
    public List<McpToolInfo> getAllMcpTools() {
        return mcpManager.getAllToolInfos();
    }

    /**
     * Generate unique session ID.
     */
    private String generateSessionId() {
        return "session_" + java.util.UUID.randomUUID().toString().substring(0, 8);
    }

    /**
     * Create AgentHarness from environment variables.
     *
     * <p>Supported environment variables:</p>
     * <ul>
     *   <li>ANTHROPIC_API_KEY / OPENAI_API_KEY: API key</li>
     *   <li>HARNESS_MODEL: Model name (default: claude-sonnet-4-6)</li>
     *   <li>HARNESS_PROVIDER: Provider (anthropic/openai/auto)</li>
     *   <li>HARNESS_BASE_URL: Custom API endpoint</li>
     *   <li>HARNESS_MAX_ITERATIONS: Max loop iterations</li>
     *   <li>HARNESS_SYSTEM_PROMPT: System prompt</li>
     *   <li>HARNESS_MEMORY_DIR: Memory directory</li>
     *   <li>HARNESS_SANDBOX_WORKSPACE: Sandbox workspace path</li>
     * </ul>
     *
     * <p>Example:</p>
     * <pre>{@code
     * // Set environment variables
     * // ANTHROPIC_API_KEY=sk-ant-...
     * // HARNESS_MODEL=claude-sonnet-4-6
     *
     * AgentHarness agent = AgentHarness.fromEnv();
     * LoopResult result = agent.run("Hello").join();
     * }</pre>
     *
     * @return AgentHarness configured from environment variables
     */
    public static AgentHarness fromEnv() {
        HarnessConfig config = HarnessConfig.fromEnv();
        return new AgentHarness(config);
    }

    /**
     * Create AgentHarness from environment variables with tools.
     *
     * @param tools Tools to register
     * @return AgentHarness configured from environment variables
     */
    public static AgentHarness fromEnv(List<Tool> tools) {
        HarnessConfig config = HarnessConfig.fromEnv();
        return new AgentHarness(config) {{
            for (Tool tool : tools) {
                registerTool(tool);
            }
        }};
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