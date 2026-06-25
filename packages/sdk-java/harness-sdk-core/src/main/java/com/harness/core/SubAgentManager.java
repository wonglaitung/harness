package com.harness.core;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.types.LoopResult;
import com.harness.types.LoopState;
import com.harness.types.Message;
import com.harness.types.TokenUsage;

/**
 * Manages sub-agents for task delegation.
 *
 * Sub-agents allow the main agent to delegate sub-tasks to specialized child agents.
 * This is useful for:
 * - Task decomposition: Break large tasks into smaller, manageable pieces
 * - Parallel processing: Run multiple sub-agents concurrently
 * - Isolation: Each sub-agent has its own context window
 *
 * Example:
 * <pre>
 * SubAgentManager manager = new SubAgentManager();
 *
 * // Spawn sub-agents for parallel analysis
 * manager.spawn(SubAgentConfig.builder()
 *     .name("core_analyzer")
 *     .task("Analyze src/core directory")
 *     .build());
 * manager.spawn(SubAgentConfig.builder()
 *     .name("tools_analyzer")
 *     .task("Analyze src/tools directory")
 *     .build());
 *
 * // Run all sub-agents in parallel
 * Map&lt;String, SubAgentResult&gt; results = manager.runAll().join();
 *
 * for (Map.Entry&lt;String, SubAgentResult&gt; entry : results.entrySet()) {
 *     System.out.println(entry.getKey() + ": " + entry.getValue().summary());
 * }
 * </pre>
 */
public class SubAgentManager {

    private static final Logger logger = LoggerFactory.getLogger(SubAgentManager.class);

    private final Map<String, SubAgentRunner> subAgents = new ConcurrentHashMap<>();
    private final Map<String, SubAgentConfig> configs = new ConcurrentHashMap<>();
    private final Map<String, SubAgentResult> results = new ConcurrentHashMap<>();
    private final Map<String, SubAgentStatus> statuses = new ConcurrentHashMap<>();

    public SubAgentManager() {
    }

    /**
     * Create a new sub-agent.
     *
     * @param config Configuration for the sub-agent
     * @return The name of the created sub-agent
     */
    public String spawn(SubAgentConfig config) {
        String name = config.name();
        subAgents.put(name, new SubAgentRunner(config));
        configs.put(name, config);
        statuses.put(name, SubAgentStatus.PENDING);
        logger.info("Spawned sub-agent: {}", name);
        return name;
    }

    /**
     * Run a specific sub-agent.
     *
     * @param name Name of the sub-agent to run
     * @return CompletableFuture with the result
     */
    public CompletableFuture<SubAgentResult> run(String name) {
        SubAgentRunner runner = subAgents.get(name);
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
                // Simulate sub-agent execution
                // In a real implementation, this would create a new AgentHarness
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
     *
     * @return CompletableFuture with all results
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
     * Internal runner for sub-agents.
     */
    private static class SubAgentRunner {
        private final SubAgentConfig config;

        SubAgentRunner(SubAgentConfig config) {
            this.config = config;
        }

        SubAgentResult run() {
            // Build default prompt if not provided
            String systemPrompt = config.systemPrompt() != null
                ? config.systemPrompt()
                : buildDefaultPrompt(config);

            // Simulate execution
            // In a real implementation, this would create and run an AgentHarness
            String summary = "Sub-agent '" + config.name() + "' completed task: " + config.task();

            return SubAgentResult.success(
                config.name(),
                summary,
                1,
                new TokenUsage(100, 50)
            );
        }

        private String buildDefaultPrompt(SubAgentConfig config) {
            return String.format(
                "You are a specialized sub-agent tasked with: %s\n\n" +
                "You are part of a larger task and should focus only on your assigned work.\n" +
                "Complete your task thoroughly and report your findings clearly.\n\n" +
                "When finished, provide a concise summary of what you accomplished.",
                config.task()
            );
        }
    }
}
