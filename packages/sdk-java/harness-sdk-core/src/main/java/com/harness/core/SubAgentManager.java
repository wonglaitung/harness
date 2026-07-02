package com.harness.core;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Function;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Manages sub-agents for task delegation.
 *
 * Sub-agents allow the main agent to delegate sub-tasks to specialized child agents.
 * This is useful for:
 * - Task decomposition: Break large tasks into smaller, manageable pieces
 * - Parallel processing: Run multiple sub-agents concurrently
 * - Isolation: Each sub-agent has its own context window
 *
 * Design:
 * This manager uses an AgentFactory interface to create sub-agent runners,
 * allowing it to work with any agent implementation (AgentHarness, MockHarness, etc.)
 *
 * Example:
 * <pre>
 * // Create with factory that wraps AgentHarness
 * SubAgentManager manager = new SubAgentManager(agentFactory);
 *
 * // Spawn sub-agents for parallel analysis
 * manager.spawn(SubAgentConfig.builder()
 *     .name("core_analyzer")
 *     .task("Analyze src/core directory")
 *     .tools(List.of("read", "glob", "grep"))
 *     .build());
 *
 * // Run all sub-agents in parallel
 * Map&lt;String, SubAgentResult&gt; results = manager.runAll().join();
 * </pre>
 */
public class SubAgentManager {

    private static final Logger logger = LoggerFactory.getLogger(SubAgentManager.class);

    // Tool aliases for common tool name mappings
    private static final Map<String, String> TOOL_ALIASES = new HashMap<>();
    static {
        TOOL_ALIASES.put("read", "read");
        TOOL_ALIASES.put("write", "write_file");
        TOOL_ALIASES.put("edit", "edit_file");
        TOOL_ALIASES.put("glob", "glob");
        TOOL_ALIASES.put("grep", "grep");
        TOOL_ALIASES.put("bash", "bash");
        TOOL_ALIASES.put("websearch", "web_search");
        TOOL_ALIASES.put("webfetch", "web_fetch");
    }

    private final AgentFactory agentFactory;
    private final AgentHarnessParent parent;

    private final Map<String, AgentRunner> subAgents = new ConcurrentHashMap<>();
    private final Map<String, SubAgentConfig> configs = new ConcurrentHashMap<>();
    private final Map<String, SubAgentResult> results = new ConcurrentHashMap<>();
    private final Map<String, SubAgentStatus> statuses = new ConcurrentHashMap<>();

    /**
     * Create SubAgentManager with a default mock factory.
     *
     * This constructor is for testing and simple use cases where
     * real agent execution is not needed.
     */
    public SubAgentManager() {
        this.parent = null;
        this.agentFactory = new MockAgentFactory();
    }

    /**
     * Create SubAgentManager with agent factory.
     *
     * @param agentFactory Factory to create sub-agent runners
     */
    public SubAgentManager(AgentFactory agentFactory) {
        this.agentFactory = agentFactory;
        this.parent = null;
    }

    /**
     * Create SubAgentManager with parent agent reference.
     *
     * @param parent The parent agent for tool/LLM inheritance
     * @param agentFactory Factory to create sub-agent runners
     */
    public SubAgentManager(AgentHarnessParent parent, AgentFactory agentFactory) {
        this.parent = parent;
        this.agentFactory = agentFactory;
    }

    /**
     * Spawn a new sub-agent.
     *
     * @param config Configuration for the sub-agent
     * @return The name of the created sub-agent
     */
    public String spawn(SubAgentConfig config) {
        String name = config.name();

        try {
            // Create agent runner via factory
            List<Tool> tools = filterTools(parent != null ? parent.getAllTools() : List.of(), config.tools());
            AgentRunner runner = agentFactory.createRunner(config, tools, parent);

            subAgents.put(name, runner);
            configs.put(name, config);
            statuses.put(name, SubAgentStatus.PENDING);
            logger.info("Spawned sub-agent: {} (tools: {})", name,
                config.tools() != null ? config.tools() : "all inherited");
            return name;
        } catch (Exception e) {
            logger.error("Failed to spawn sub-agent {}: {}", name, e.getMessage());
            statuses.put(name, SubAgentStatus.FAILED);
            results.put(name, SubAgentResult.failure(name, "Spawn failed: " + e.getMessage()));
            return name;
        }
    }

    /**
     * Filter tools based on allowed tool names.
     */
    private List<Tool> filterTools(List<Tool> allTools, List<String> allowedNames) {
        if (allowedNames == null) {
            return new ArrayList<>(allTools);
        }

        // Build set of allowed tool names (including aliases)
        Map<String, String> nameLookup = new HashMap<>();
        for (String name : allowedNames) {
            nameLookup.put(name, name);
            if (TOOL_ALIASES.containsKey(name)) {
                nameLookup.put(TOOL_ALIASES.get(name), name);
            }
            for (Map.Entry<String, String> entry : TOOL_ALIASES.entrySet()) {
                if (entry.getValue().equals(name)) {
                    nameLookup.put(entry.getKey(), name);
                }
            }
        }

        List<Tool> filtered = new ArrayList<>();
        for (Tool tool : allTools) {
            if (nameLookup.containsKey(tool.name())) {
                filtered.add(tool);
            }
        }

        return filtered;
    }

    /**
     * Run a specific sub-agent.
     */
    public CompletableFuture<SubAgentResult> run(String name) {
        AgentRunner runner = subAgents.get(name);
        SubAgentConfig config = configs.get(name);

        if (runner == null || config == null) {
            return CompletableFuture.completedFuture(
                SubAgentResult.failure(name, "Sub-agent not found: " + name)
            );
        }

        statuses.put(name, SubAgentStatus.RUNNING);
        logger.info("Running sub-agent: {}", name);

        return CompletableFuture.supplyAsync(() -> {
            try {
                SubAgentResult result = runner.run();
                results.put(name, result);
                statuses.put(name, result.status());
                logger.info("Sub-agent {} completed: success={}", name, result.success());
                return result;
            } catch (Exception e) {
                logger.error("Sub-agent {} failed: {}", name, e.getMessage());
                SubAgentResult result = SubAgentResult.failure(name, e.getMessage());
                results.put(name, result);
                statuses.put(name, SubAgentStatus.FAILED);
                return result;
            }
        });
    }

    /**
     * Run all pending sub-agents in parallel.
     */
    public CompletableFuture<Map<String, SubAgentResult>> runAll() {
        List<String> pending = new ArrayList<>();
        for (Map.Entry<String, SubAgentStatus> entry : statuses.entrySet()) {
            if (entry.getValue() == SubAgentStatus.PENDING) {
                pending.add(entry.getKey());
            }
        }

        List<CompletableFuture<SubAgentResult>> futures = new ArrayList<>();
        for (String name : pending) {
            futures.add(run(name));
        }

        return CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]))
            .thenApply(v -> {
                Map<String, SubAgentResult> allResults = new HashMap<>();
                for (String name : pending) {
                    allResults.put(name, results.get(name));
                }
                return allResults;
            });
    }

    /**
     * Get the result of a specific sub-agent.
     */
    public SubAgentResult getResult(String name) {
        return results.get(name);
    }

    /**
     * Get the status of a specific sub-agent.
     */
    public SubAgentStatus getStatus(String name) {
        return statuses.get(name);
    }

    /**
     * Get all collected results.
     */
    public Map<String, SubAgentResult> getAllResults() {
        return new HashMap<>(results);
    }

    /**
     * List all sub-agent names.
     */
    public List<String> listSubAgents() {
        return new ArrayList<>(subAgents.keySet());
    }

    /**
     * Cancel a running sub-agent.
     */
    public boolean cancel(String name) {
        if (statuses.get(name) != SubAgentStatus.RUNNING) {
            return false;
        }

        statuses.put(name, SubAgentStatus.CANCELLED);
        results.put(name, SubAgentResult.cancelled(name));
        logger.info("Cancelled sub-agent: {}", name);
        return true;
    }

    /**
     * Clear all sub-agents and results.
     */
    public void clear() {
        subAgents.clear();
        configs.clear();
        results.clear();
        statuses.clear();
    }

    /**
     * Interface for creating agent runners.
     *
     * Implemented by integration module to wrap AgentHarness.
     */
    public interface AgentFactory {
        AgentRunner createRunner(SubAgentConfig config, List<Tool> tools, AgentHarnessParent parent);
    }

    /**
     * Interface for running a sub-agent.
     */
    public interface AgentRunner {
        SubAgentResult run();
    }

    /**
     * Interface for parent agent reference.
     */
    public interface AgentHarnessParent {
        String getModel();
        Object getLLMClient();  // Returns LLMClient but typed as Object to avoid circular dependency
        List<Tool> getAllTools();
    }

    /**
     * Default mock factory for testing and simple use cases.
     */
    private static class MockAgentFactory implements AgentFactory {
        @Override
        public AgentRunner createRunner(SubAgentConfig config, List<Tool> tools, AgentHarnessParent parent) {
            return new MockAgentRunner(config);
        }
    }

    /**
     * Mock runner that simulates agent execution.
     */
    private static class MockAgentRunner implements AgentRunner {
        private final SubAgentConfig config;

        MockAgentRunner(SubAgentConfig config) {
            this.config = config;
        }

        @Override
        public SubAgentResult run() {
            // Simulate execution with placeholder result
            String summary = "Sub-agent '" + config.name() + "' completed task: " + config.task();
            return SubAgentResult.success(
                config.name(),
                summary,
                1,
                new com.harness.types.TokenUsage(100, 50)
            );
        }
    }
}
