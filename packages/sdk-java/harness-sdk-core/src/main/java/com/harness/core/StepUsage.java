package com.harness.core;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;

/**
 * Current step budget usage.
 *
 * @param iterations Number of iterations completed
 * @param toolCallsTotal Total tool calls in this task
 * @param toolCallsThisStep Tool calls in current step (current LLM response)
 * @param toolCallsByTool Per-tool call counts
 * @param taskStartTime When the task started
 * @param lastStepTime When the last step started
 */
public record StepUsage(
    int iterations,
    int toolCallsTotal,
    int toolCallsThisStep,
    Map<String, Integer> toolCallsByTool,
    Instant taskStartTime,
    Instant lastStepTime
) {

    public StepUsage() {
        this(0, 0, 0, new HashMap<>(), Instant.now(), Instant.now());
    }

    /**
     * Reset step-level counters (after each LLM response).
     */
    public StepUsage resetStep() {
        return new StepUsage(
            iterations, toolCallsTotal, 0, toolCallsByTool,
            taskStartTime, Instant.now()
        );
    }

    /**
     * Increment iterations.
     */
    public StepUsage incrementIterations() {
        return new StepUsage(
            iterations + 1, toolCallsTotal, toolCallsThisStep, toolCallsByTool,
            taskStartTime, lastStepTime
        );
    }

    /**
     * Record a tool call.
     */
    public StepUsage recordToolCall(String toolName) {
        Map<String, Integer> newByTool = new HashMap<>(toolCallsByTool);
        newByTool.merge(toolName, 1, Integer::sum);

        return new StepUsage(
            iterations, toolCallsTotal + 1, toolCallsThisStep + 1, newByTool,
            taskStartTime, lastStepTime
        );
    }

    /**
     * Serialize to map.
     */
    public Map<String, Object> toMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("iterations", iterations);
        map.put("toolCallsTotal", toolCallsTotal);
        map.put("toolCallsThisStep", toolCallsThisStep);
        map.put("toolCallsByTool", toolCallsByTool);
        map.put("taskStartTime", taskStartTime.toString());
        map.put("lastStepTime", lastStepTime.toString());
        return map;
    }
}
