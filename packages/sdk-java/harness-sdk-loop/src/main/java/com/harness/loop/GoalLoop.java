package com.harness.loop;

import com.harness.loop.types.GoalConfig;
import com.harness.loop.types.GoalResult;
import com.harness.loop.types.GoalStatus;
import com.harness.loop.types.VerificationRecord;
import com.harness.loop.types.VerificationResult;
import com.harness.types.LoopResult;
import com.harness.types.Session;
import com.harness.types.TokenUsage;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;

/**
 * Goal-driven execution loop.
 *
 * <p>Continues execution until one of the following:</p>
 * <ul>
 *   <li>Goal is achieved (verified)</li>
 *   <li>Max iterations reached</li>
 *   <li>Max context resets reached</li>
 *   <li>Timeout exceeded</li>
 *   <li>Error occurs</li>
 * </ul>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * AgentHarness agent = new AgentHarness(llmClient, config);
 * GoalConfig goalConfig = GoalConfig.builder()
 *     .description("Fix all type errors")
 *     .build();
 *
 * GoalLoop loop = new GoalLoop(agent, goalConfig);
 * GoalResult result = loop.run().join();
 *
 * if (result.achieved()) {
 *     System.out.println("Goal achieved in " + result.totalIterations() + " iterations");
 * }
 * }</pre>
 */
public class GoalLoop {
    private static final Logger logger = LoggerFactory.getLogger(GoalLoop.class);

    // Prompt templates
    private static final String INITIAL_PROMPT_TEMPLATE = """
# Goal: %s

Please work towards achieving this goal. You can use tools to make progress.

## Success Criteria
%s

## Instructions
1. Break down the goal into actionable steps
2. Use tools to make progress
3. Verify your work at each step
4. Continue until the goal is fully achieved

Take action and report your progress. Continue until the goal is achieved.""";

    private static final String CONTINUATION_PROMPT_TEMPLATE = """
# Goal Continuation

The previous context was reset due to size limits. Continue working towards the goal.

## Original Goal
%s

## Previous Progress
%s

## Current Status
- Iterations completed: %d
- Context resets: %d

## Instructions
Continue from where you left off. Focus on completing the remaining work.
Do not repeat what was already done. Proceed with the next steps.""";

    private static final String NEXT_STEP_PROMPT_TEMPLATE = """
The goal is not yet achieved.

## Verification Feedback
%s

## Current Progress
%s

## What's Still Needed
Based on the verification feedback, continue working towards:
%s

Take the next step to make progress. Focus on what remains to be done.""";

    /**
     * Interface for agent that can run prompts.
     * This allows GoalLoop to work with any agent implementation.
     */
    public interface AgentRunner {
        /**
         * Run the agent with a prompt.
         */
        CompletableFuture<LoopResult> run(String prompt, String sessionId);

        /**
         * Run the agent with a prompt and progress callback.
         */
        CompletableFuture<LoopResult> run(String prompt, String sessionId, Consumer<Object> onProgress);

        /**
         * Get a session by ID.
         */
        Session getSession(String sessionId);

        /**
         * Get the context window size.
         */
        int getContextWindow();
    }

    private final AgentRunner agent;
    private final GoalConfig config;
    private final Consumer<Object> onProgress;
    private final GoalVerifier verifier;

    // State tracking
    private int iteration = 0;
    private int contextResets = 0;
    private long startTime = 0;
    private String sessionId = "";
    private int totalInputTokens = 0;
    private int totalOutputTokens = 0;
    private int totalAgentIterations = 0;
    private final List<VerificationRecord> verificationLog = new ArrayList<>();

    /**
     * Create a new GoalLoop.
     *
     * @param agent The agent runner
     * @param config Goal configuration
     */
    public GoalLoop(AgentRunner agent, GoalConfig config) {
        this(agent, config, null);
    }

    /**
     * Create a new GoalLoop with progress callback.
     *
     * @param agent The agent runner
     * @param config Goal configuration
     * @param onProgress Optional progress callback
     */
    public GoalLoop(AgentRunner agent, GoalConfig config, Consumer<Object> onProgress) {
        this.agent = agent;
        this.config = config;
        this.onProgress = onProgress;
        this.verifier = new GoalVerifier(config);
    }

    /**
     * Run the goal-driven loop.
     *
     * @return CompletableFuture with GoalResult
     */
    public CompletableFuture<GoalResult> run() {
        // Initialize state
        iteration = 0;
        contextResets = 0;
        startTime = System.currentTimeMillis();
        sessionId = "goal-" + UUID.randomUUID().toString().substring(0, 8);
        totalInputTokens = 0;
        totalOutputTokens = 0;
        totalAgentIterations = 0;
        verificationLog.clear();

        // Build initial prompt
        String currentPrompt = buildInitialPrompt();

        logger.info("Starting goal loop: {}...", config.getDescription().substring(0, Math.min(100, config.getDescription().length())));

        return runLoop(currentPrompt);
    }

    private CompletableFuture<GoalResult> runLoop(String currentPrompt) {
        // Check timeout
        if (checkTimeout()) {
            return CompletableFuture.completedFuture(createResult(GoalStatus.TIMEOUT, null, null));
        }

        // Check max iterations
        if (iteration >= config.getMaxIterations()) {
            logger.warn("Max iterations ({}) reached", config.getMaxIterations());
            return CompletableFuture.completedFuture(createResult(GoalStatus.MAX_ITERATIONS, null, null));
        }

        // Check max context resets
        if (contextResets > config.getMaxContextResets()) {
            logger.warn("Max context resets ({}) exceeded", config.getMaxContextResets());
            return CompletableFuture.completedFuture(createResult(GoalStatus.MAX_RESETS, null, null));
        }

        // Run agent
        logger.debug("Running agent iteration {}", iteration + 1);
        return agent.run(currentPrompt, sessionId, onProgress)
                .thenCompose(result -> {
                    iteration++;

                    // Accumulate agent loop internal iterations
                    if (result.iterations() > 0) {
                        totalAgentIterations += result.iterations();
                    }

                    // Update token usage
                    if (result.tokenUsage() != null) {
                        totalInputTokens += result.tokenUsage().inputTokens();
                        totalOutputTokens += result.tokenUsage().outputTokens();
                    }

                    // Check cost control
                    if (checkCostExceeded()) {
                        return CompletableFuture.completedFuture(
                                createResult(GoalStatus.ERROR, null, "Cost budget exceeded"));
                    }

                    // Verify goal
                    return verifyGoal(result)
                            .thenCompose(verification -> {
                                if (verification.isAchieved()) {
                                    logger.info("Goal achieved after {} iterations", iteration);
                                    return CompletableFuture.completedFuture(
                                            createResult(GoalStatus.ACHIEVED, result, null));
                                }

                                // Check if we need context reset
                                if (shouldResetContext(result)) {
                                    contextResets++;
                                    logger.info("Context reset {}/{}", contextResets, config.getMaxContextResets());

                                    // Create new session for fresh context
                                    sessionId = "goal-" + UUID.randomUUID().toString().substring(0, 8);
                                    String continuationPrompt = buildContinuationPrompt(result);

                                    emitProgress("context_reset", "Resetting context to prevent overflow",
                                            Map.of("reset_count", contextResets));

                                    return runLoop(continuationPrompt);
                                } else {
                                    // Continue in same session
                                    String nextPrompt = buildNextStepPrompt(result, verification);
                                    return runLoop(nextPrompt);
                                }
                            });
                })
                .exceptionally(error -> {
                    logger.error("Goal loop error: {}", error.getMessage());
                    return createResult(GoalStatus.ERROR, null, error.getMessage());
                });
    }

    private CompletableFuture<VerificationResult> verifyGoal(LoopResult result) {
        // Build GoalResult for verification
        GoalResult goalResult = new GoalResult.Builder()
                .goal(config.getDescription())
                .status(GoalStatus.MAX_ITERATIONS) // Temporary status
                .totalIterations(iteration)
                .finalResponse(result.content())
                .build();

        Map<String, Object> context = new HashMap<>();
        context.put("workspace_dir", config.getWorkspaceDir());

        return verifier.verify(goalResult, context)
                .thenApply(verification -> {
                    // Record verification
                    VerificationRecord record = new VerificationRecord.Builder()
                            .iteration(iteration)
                            .achieved(verification.isAchieved())
                            .confidence(verification.getConfidence())
                            .reasoning(verification.getReasoning())
                            .build();
                    verificationLog.add(record);

                    emitProgress("verification",
                            "Verification: " + (verification.isAchieved() ? "achieved" : "not achieved"),
                            Map.of(
                                    "achieved", verification.isAchieved(),
                                    "confidence", verification.getConfidence(),
                                    "reasoning", verification.getReasoning() != null &&
                                            verification.getReasoning().length() > 200
                                            ? verification.getReasoning().substring(0, 200)
                                            : verification.getReasoning()
                            ));

                    return verification;
                });
    }

    private boolean shouldResetContext(LoopResult result) {
        // Check token usage ratio
        int contextWindow = agent.getContextWindow();
        if (contextWindow > 0) {
            int usedTokens = totalInputTokens + totalOutputTokens;
            double ratio = (double) usedTokens / contextWindow;
            if (ratio >= config.getContextResetThreshold()) {
                logger.debug("Context reset triggered: {:.1%} of context used", ratio);
                return true;
            }
        }

        // Check message count (fallback heuristic)
        Session session = agent.getSession(sessionId);
        if (session != null && session.messages().size() > 50) {
            logger.debug("Context reset triggered: {} messages", session.messages().size());
            return true;
        }

        return false;
    }

    private boolean checkTimeout() {
        long elapsed = System.currentTimeMillis() - startTime;
        return elapsed >= config.getTimeoutSeconds() * 1000L;
    }

    private boolean checkCostExceeded() {
        if (config.getMaxTokens() == null && config.getMaxCostUsd() == null) {
            return false;
        }

        int totalTokens = totalInputTokens + totalOutputTokens;

        // Check token budget
        if (config.getMaxTokens() != null && totalTokens >= config.getMaxTokens()) {
            return true;
        }

        // Check cost budget (USD)
        // TODO: Implement cost tracking when pricing info is available
        if (config.getMaxCostUsd() != null) {
            // Placeholder for cost calculation
        }

        return false;
    }

    private GoalResult createResult(GoalStatus status, LoopResult result, String error) {
        double duration = (System.currentTimeMillis() - startTime) / 1000.0;

        Map<String, Integer> totalTokens = new HashMap<>();
        totalTokens.put("input", totalInputTokens);
        totalTokens.put("output", totalOutputTokens);

        return new GoalResult.Builder()
                .goal(config.getDescription())
                .status(status)
                .totalIterations(totalAgentIterations)
                .contextResets(contextResets)
                .totalTokens(totalTokens)
                .durationSeconds(duration)
                .finalResponse(result != null ? result.content() : "")
                .session(result != null ? result.session() : null)
                .verificationLog(new ArrayList<>(verificationLog))
                .error(error)
                .build();
    }

    private String buildInitialPrompt() {
        String successCriteria = config.getSuccessCriteria() != null
                ? config.getSuccessCriteria()
                : "Goal is achieved when the task is complete and verified.";

        return String.format(INITIAL_PROMPT_TEMPLATE, config.getDescription(), successCriteria);
    }

    private String buildContinuationPrompt(LoopResult result) {
        // Truncate previous response if too long
        int maxResponseLen = 1000;
        String previousResponse = result.content() != null ? result.content() : "";
        if (previousResponse.length() > maxResponseLen) {
            previousResponse = previousResponse.substring(0, maxResponseLen) + "\n... (truncated)";
        }

        return String.format(CONTINUATION_PROMPT_TEMPLATE,
                config.getDescription(),
                previousResponse,
                iteration,
                contextResets);
    }

    private String buildNextStepPrompt(LoopResult result, VerificationResult verification) {
        // Truncate progress if too long
        int maxProgressLen = 500;
        String progress = result.content() != null ? result.content() : "";
        if (progress.length() > maxProgressLen) {
            progress = progress.substring(0, maxProgressLen) + "\n... (truncated)";
        }

        return String.format(NEXT_STEP_PROMPT_TEMPLATE,
                config.getDescription(),
                verification.getReasoning() != null ? verification.getReasoning() : "No specific feedback",
                progress);
    }

    private void emitProgress(String eventType, String message, Map<String, Object> data) {
        if (onProgress == null) {
            return;
        }

        // Create a simple progress event object
        Map<String, Object> event = new HashMap<>();
        event.put("type", eventType);
        event.put("message", message);
        event.put("data", data);
        event.put("iteration", iteration);

        onProgress.accept(event);
    }

    /**
     * Get the verification history (read-only).
     */
    public List<VerificationRecord> getVerificationHistory() {
        return List.copyOf(verificationLog);
    }
}
