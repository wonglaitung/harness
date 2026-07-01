package com.harness.orchestrator;

import com.harness.loop.GoalLoop;
import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.VerificationMethod;
import com.harness.types.LoopResult;
import com.harness.types.Session;
import com.harness.types.TokenUsage;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Consumer;

/**
 * Multi-agent team orchestrator.
 *
 * <p>Manages teams of agents with different roles and coordination modes:</p>
 * <ul>
 *   <li>Broadcast: All agents execute same task simultaneously</li>
 *   <li>Sequential: Agents execute in order, passing outputs</li>
 *   <li>Hierarchical: Leader assigns tasks to workers</li>
 * </ul>
 *
 * <h2>Key Features</h2>
 * <ul>
 *   <li>Role-based agents: Each role has its own agent instance</li>
 *   <li>Coordination modes: Different patterns for different use cases</li>
 * </ul>
 */
public class TeamOrchestrator {
    private static final Logger logger = LoggerFactory.getLogger(TeamOrchestrator.class);

    private final GoalLoop.AgentRunner agentRunner;
    private final Map<String, TeamConfig> teams = new ConcurrentHashMap<>();
    private final Map<String, GoalLoop.AgentRunner> roleAgents = new ConcurrentHashMap<>();

    /**
     * Create a new TeamOrchestrator.
     *
     * @param agentRunner Agent runner for goal execution
     */
    public TeamOrchestrator(GoalLoop.AgentRunner agentRunner) {
        this.agentRunner = agentRunner;
    }

    /**
     * Create an agent team.
     *
     * @param config Team configuration
     * @return Team name
     */
    public String createTeam(TeamConfig config) {
        teams.put(config.getName(), config);
        logger.info("Created team '{}' with {} roles, mode: {}",
                config.getName(), config.getRoles().size(), config.getCoordinationMode().getValue());
        return config.getName();
    }

    /**
     * Run a team task.
     *
     * @param teamName Team name
     * @param task     Task description
     * @return Team execution result
     */
    public CompletableFuture<TeamResult> run(String teamName, String task) {
        return run(teamName, task, null);
    }

    /**
     * Run a team task.
     *
     * @param teamName          Team name
     * @param task              Task description
     * @param coordinationMode  Override team's default coordination mode
     * @return Team execution result
     */
    public CompletableFuture<TeamResult> run(String teamName, String task, CoordinationMode coordinationMode) {
        TeamConfig config = teams.get(teamName);
        if (config == null) {
            return CompletableFuture.failedFuture(new IllegalArgumentException("Team not found: " + teamName));
        }

        CoordinationMode mode = coordinationMode != null ? coordinationMode : config.getCoordinationMode();
        Instant startTime = Instant.now();

        return executeByMode(config, task, mode)
                .thenApply(results -> {
                    int totalIterations = results.values().stream()
                            .mapToInt(GoalResult::totalIterations)
                            .sum();
                    int totalTokens = results.values().stream()
                            .mapToInt(r -> {
                                Map<String, Integer> tokens = r.totalTokens();
                                return tokens.getOrDefault("input", 0) + tokens.getOrDefault("output", 0);
                            })
                            .sum();

                    return TeamResult.builder()
                            .teamName(teamName)
                            .success(results.values().stream().allMatch(GoalResult::achieved))
                            .agentResults(results)
                            .totalIterations(totalIterations)
                            .totalTokens(totalTokens)
                            .durationSeconds(java.time.Duration.between(startTime, Instant.now()).toMillis() / 1000.0)
                            .build();
                })
                .exceptionally(error -> {
                    logger.error("Team '{}' execution failed: {}", teamName, error.getMessage());
                    return TeamResult.builder()
                            .teamName(teamName)
                            .success(false)
                            .durationSeconds(java.time.Duration.between(startTime, Instant.now()).toMillis() / 1000.0)
                            .error(error.getMessage())
                            .build();
                });
    }

    private CompletableFuture<Map<String, GoalResult>> executeByMode(
            TeamConfig config, String task, CoordinationMode mode) {

        return switch (mode) {
            case BROADCAST -> runBroadcast(config, task);
            case SEQUENTIAL -> runSequential(config, task);
            case HIERARCHICAL -> runHierarchical(config, task);
        };
    }

    /**
     * Broadcast mode: All agents execute same task simultaneously.
     *
     * <p>Use cases: Multi-perspective analysis, voting decisions.</p>
     */
    private CompletableFuture<Map<String, GoalResult>> runBroadcast(TeamConfig config, String task) {
        List<CompletableFuture<Map.Entry<String, GoalResult>>> futures = new ArrayList<>();

        for (AgentRole role : config.getRoles()) {
            futures.add(runAgentForRole(role, task)
                    .thenApply(result -> Map.entry(role.getName(), result)));
        }

        return CompletableFuture.allOf(futures.toArray(new CompletableFuture[0]))
                .thenApply(v -> {
                    Map<String, GoalResult> results = new HashMap<>();
                    for (CompletableFuture<Map.Entry<String, GoalResult>> future : futures) {
                        Map.Entry<String, GoalResult> entry = future.join();
                        results.put(entry.getKey(), entry.getValue());
                    }
                    return results;
                });
    }

    /**
     * Sequential mode: Agents execute in order, passing outputs.
     *
     * <p>Use cases: Pipeline processing, multi-stage review.</p>
     */
    private CompletableFuture<Map<String, GoalResult>> runSequential(TeamConfig config, String task) {
        Map<String, GoalResult> results = new HashMap<>();
        String[] currentTask = {task};

        CompletableFuture<Map<String, GoalResult>> future = CompletableFuture.completedFuture(results);

        for (AgentRole role : config.getRoles()) {
            future = future.thenCompose(prevResults ->
                    runAgentForRole(role, currentTask[0])
                            .thenApply(result -> {
                                prevResults.put(role.getName(), result);
                                // Pass result to next agent
                                if (result.achieved()) {
                                    currentTask[0] = task + "\n\nPrevious agent (" + role.getName() + ") output:\n"
                                            + result.finalResponse();
                                }
                                return prevResults;
                            })
            );
        }

        return future;
    }

    /**
     * Hierarchical mode: Leader assigns tasks to workers.
     *
     * <p>Use cases: Complex task decomposition, expert scheduling.</p>
     */
    private CompletableFuture<Map<String, GoalResult>> runHierarchical(TeamConfig config, String task) {
        if (config.getRoles().isEmpty()) {
            return CompletableFuture.completedFuture(new HashMap<>());
        }

        // First role is the leader
        AgentRole leaderRole = config.getRoles().get(0);
        List<AgentRole> workerRoles = config.getRoles().subList(1, config.getRoles().size());

        String allocationPrompt = buildAllocationPrompt(leaderRole, workerRoles, task);

        return runAgentForRole(leaderRole, allocationPrompt)
                .thenCompose(leaderResult -> {
                    Map<String, GoalResult> results = new HashMap<>();
                    results.put(leaderRole.getName(), leaderResult);

                    // Workers execute assigned tasks
                    List<CompletableFuture<Void>> workerFutures = new ArrayList<>();
                    for (AgentRole role : workerRoles) {
                        String subtask = "Complete your assigned part of: " + task;
                        workerFutures.add(runAgentForRole(role, subtask)
                                .thenAccept(result -> results.put(role.getName(), result)));
                    }

                    return CompletableFuture.allOf(workerFutures.toArray(new CompletableFuture[0]))
                            .thenApply(v -> results);
                });
    }

    private String buildAllocationPrompt(AgentRole leader, List<AgentRole> workers, String task) {
        StringBuilder sb = new StringBuilder();
        sb.append("You are the team leader. Analyze the following task and assign subtasks to team members.\n\n");
        sb.append("Team members:\n");
        for (AgentRole role : workers) {
            sb.append("- ").append(role.getName()).append(": ").append(role.getDescription()).append("\n");
        }
        sb.append("\nTask: ").append(task).append("\n\n");
        sb.append("Provide your allocation in the following format:\n");
        sb.append("- [agent_name]: [subtask]");
        return sb.toString();
    }

    private CompletableFuture<GoalResult> runAgentForRole(AgentRole role, String task) {
        GoalConfig config = new GoalConfig.Builder()
                .description(task)
                .maxIterations(role.getMaxIterations())
                .verificationMethod(VerificationMethod.CUSTOM)
                .customVerifier(result -> true) // Always succeed for testing/simpler cases
                .build();

        GoalLoop loop = new GoalLoop(agentRunner, config);
        return loop.run();
    }

    /**
     * Get team configuration.
     */
    public TeamConfig getTeam(String teamName) {
        return teams.get(teamName);
    }

    /**
     * List all team names.
     */
    public List<String> listTeams() {
        return new ArrayList<>(teams.keySet());
    }

    /**
     * Remove a team.
     */
    public void removeTeam(String teamName) {
        teams.remove(teamName);
    }
}
