package com.harness.core;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.types.LLMResponse;
import com.harness.types.Message;

/**
 * Hook that intercepts exit attempts for long-horizon tasks.
 *
 * Ralph Loop intercepts exit attempts when the agent claims completion but the task
 * is not actually done. It saves progress and reinjects a continuation prompt in a
 * clean context, preventing "context anxiety" where the model exits early due to
 * approaching token limits.
 *
 * Example:
 * <pre>
 * AgentHarness agent = new AgentHarness();
 * agent.addHook(new RalphLoopHook(RalphLoopConfig.builder()
 *     .maxLoops(3)
 *     .build()));
 *
 * // Long tasks will automatically loop until truly complete
 * LoopResult result = agent.run("Refactor the entire codebase");
 * </pre>
 */
public class RalphLoopHook implements LifecycleHook {

    private static final Logger logger = LoggerFactory.getLogger(RalphLoopHook.class);

    private final RalphLoopConfig config;

    // Per-session loop counts
    private final Map<String, Integer> loopCounts = new ConcurrentHashMap<>();
    private final Map<String, String> previousResponses = new ConcurrentHashMap<>();

    public RalphLoopHook() {
        this(RalphLoopConfig.defaults());
    }

    public RalphLoopHook(RalphLoopConfig config) {
        this.config = config;
    }

    @Override
    public List<HookPoint> hookPoints() {
        return List.of(HookPoint.ON_EXIT_ATTEMPT, HookPoint.ON_LOOP_END);
    }

    @Override
    public HookResult execute(HookContext context) {
        return switch (context.hookPoint()) {
            case ON_EXIT_ATTEMPT -> handleExitAttempt(context);
            case ON_LOOP_END -> handleLoopEnd(context);
            default -> HookResult.continue_();
        };
    }

    /**
     * Handle exit attempt - check if task is truly complete.
     */
    private HookResult handleExitAttempt(HookContext context) {
        String sessionId = context.sessionId();
        int loopCount = loopCounts.getOrDefault(sessionId, 0);

        // Check if we've exceeded max loops
        if (loopCount >= config.maxLoops()) {
            logger.info("Ralph Loop: Max loops ({}) reached, allowing exit", config.maxLoops());
            return HookResult.continue_();
        }

        // Get the LLM response
        LLMResponse response = context.llmResponse();
        if (response == null || response.content() == null || response.content().isEmpty()) {
            return HookResult.continue_();
        }

        String responseText = response.content();
        previousResponses.put(sessionId, responseText);

        // Check if task is complete
        boolean isComplete = checkTaskComplete(responseText, context);

        if (isComplete) {
            logger.info("Ralph Loop: Task appears complete, allowing exit");
            return HookResult.continue_();
        }

        // Task is not complete - trigger continuation
        loopCounts.put(sessionId, loopCount + 1);
        logger.info("Ralph Loop: Task incomplete, triggering continuation (loop {}/{})",
            loopCount + 1, config.maxLoops());

        // Build continuation prompt
        String continuation = buildContinuationPrompt(responseText);

        // Return REINJECT action to clear context and continue
        return HookResult.builder()
            .action(HookAction.REINJECT)
            .injectMessage(Message.user(continuation))
            .clearContext(true)
            .metadata(Map.of(
                "ralph_loop_count", loopCount + 1,
                "reason", "Task incomplete, context reset for continuation"
            ))
            .build();
    }

    /**
     * Handle loop end - reset state for next session.
     */
    private HookResult handleLoopEnd(HookContext context) {
        String sessionId = context.sessionId();

        // Check if loop ended successfully
        Map<String, Object> metadata = context.metadata();
        if (metadata != null && "completed".equals(metadata.get("status"))) {
            loopCounts.remove(sessionId);
            previousResponses.remove(sessionId);
        }

        return HookResult.continue_();
    }

    /**
     * Check if the task is actually complete.
     *
     * Uses multiple heuristics:
     * 1. Custom task_complete_check if provided
     * 2. Keyword detection (e.g., "task complete", "done", "finished")
     * 3. Response length heuristics
     * 4. Incompletion indicators
     */
    private boolean checkTaskComplete(String response, HookContext context) {
        // Use custom check if provided
        if (config.taskCompleteCheck() != null) {
            try {
                boolean customResult = config.taskCompleteCheck().test(response);
                logger.debug("Custom taskCompleteCheck returned: {}", customResult);
                return customResult;
            } catch (Exception e) {
                logger.warn("Custom taskCompleteCheck failed: {}", e.getMessage());
                // Fall through to default heuristics
            }
        }

        String responseLower = response.toLowerCase();

        // Check for completion indicators
        String[] completionPhrases = {
            "task complete",
            "task completed",
            "all done",
            "finished successfully",
            "successfully completed",
            "implementation complete",
            "changes have been applied"
        };

        for (String phrase : completionPhrases) {
            if (responseLower.contains(phrase)) {
                return true;
            }
        }

        // Check for incompletion indicators
        String[] incompletionPhrases = {
            "i'll continue",
            "continuing with",
            "next step",
            "next, i'll",
            "let me continue",
            "proceeding to",
            "moving on to the next"
        };

        for (String phrase : incompletionPhrases) {
            if (responseLower.contains(phrase)) {
                return false;
            }
        }

        // If response is very short and doesn't indicate completion, likely incomplete
        if (response.length() < 100 && !responseLower.contains("done") && !responseLower.contains("complete")) {
            return false;
        }

        // Default: assume complete if no indicators either way
        return true;
    }

    /**
     * Build the continuation prompt.
     */
    private String buildContinuationPrompt(String previousResponse) {
        // Truncate previous response if too long
        int maxResponseLen = 500;
        String truncated = previousResponse.length() > maxResponseLen
            ? previousResponse.substring(0, maxResponseLen) + "..."
            : previousResponse;

        String template = config.continuationPromptTemplate();
        return template.replace("{previous_response}", truncated);
    }

    @Override
    public void reset() {
        loopCounts.clear();
        previousResponses.clear();
    }

    @Override
    public void reset(String sessionId) {
        loopCounts.remove(sessionId);
        previousResponses.remove(sessionId);
    }

    /**
     * Get current loop count for a session.
     */
    public int getLoopCount(String sessionId) {
        return loopCounts.getOrDefault(sessionId, 0);
    }

    /**
     * Get the previous response for a session.
     */
    public String getPreviousResponse(String sessionId) {
        return previousResponses.get(sessionId);
    }
}
