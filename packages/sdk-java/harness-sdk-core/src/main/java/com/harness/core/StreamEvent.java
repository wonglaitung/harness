package com.harness.core;

import com.harness.types.TokenUsage;
import com.harness.types.ToolCall;

import java.util.List;
import java.util.Map;

/**
 * Structured streaming event envelope.
 *
 * <p>Mirrors the Python SDK {@code StreamEvent}. Every streaming event carries a
 * structured envelope ({@code source}/{@code category}/{@code seq}/{@code eventId}/{@code parentId})
 * so that consumers can compose, deduplicate and causally link events across
 * nested execution (agent &rarr; goal loop).</p>
 *
 * <p>Event {@code type} values:</p>
 * <ul>
 *   <li>{@code "text"} &mdash; a text chunk (category {@code text}, source {@code agent})</li>
 *   <li>{@code "tool_calls"} &mdash; tool calls detected for the turn (category {@code tool})</li>
 *   <li>{@code "done"} &mdash; turn finished, carries {@code usage} (category {@code lifecycle})</li>
 *   <li>{@code "error"} &mdash; an error occurred (category {@code lifecycle})</li>
 *   <li>{@code "goal_start"} / {@code "goal_iteration"} / {@code "goal_verification"} / {@code "goal_done"}
 *       &mdash; goal-loop lifecycle events (source {@code goal_loop})</li>
 * </ul>
 *
 * <p>Note: {@code goalResult} is typed as {@code Object} to keep this class in the
 * low-level {@code core} module without depending on the {@code loop} module.</p>
 */
public record StreamEvent(
    String type,
    String text,
    List<ToolCall> toolCalls,
    TokenUsage usage,
    String error,
    String source,
    String category,
    int seq,
    String eventId,
    String parentId,
    Integer iteration,
    Boolean achieved,
    Object goalResult
) {

    public static final String SOURCE_AGENT = "agent";
    public static final String SOURCE_GOAL_LOOP = "goal_loop";
    public static final String SOURCE_TOOL = "tool";
    public static final String SOURCE_SYSTEM = "system";

    public static final String CATEGORY_TEXT = "text";
    public static final String CATEGORY_LIFECYCLE = "lifecycle";
    public static final String CATEGORY_TOOL = "tool";
    public static final String CATEGORY_VERIFICATION = "verification";

    /**
     * Full constructor with all envelope fields.
     */
    public StreamEvent {
        if (toolCalls == null) toolCalls = List.of();
        if (source == null) source = SOURCE_AGENT;
        if (category == null) category = CATEGORY_TEXT;
        if (usage == null) usage = new TokenUsage();
    }

    // === Factory methods ===

    /**
     * A text chunk event from the agent.
     */
    public static StreamEvent textChunk(String text, int seq) {
        return textChunk(text, seq, null);
    }

    /**
     * A text chunk event from the agent (with causal id).
     */
    public static StreamEvent textChunk(String text, int seq, String eventId) {
        return new StreamEvent(
            "text", text, List.of(), new TokenUsage(), null,
            SOURCE_AGENT, CATEGORY_TEXT, seq, eventId, null, null, null, null
        );
    }

    /**
     * A tool-calls event from the agent.
     */
    public static StreamEvent toolCalls(List<ToolCall> calls, int seq) {
        return toolCalls(calls, seq, null);
    }

    /**
     * A tool-calls event from the agent (with causal id).
     */
    public static StreamEvent toolCalls(List<ToolCall> calls, int seq, String eventId) {
        return new StreamEvent(
            "tool_calls", null, calls, new TokenUsage(), null,
            SOURCE_AGENT, CATEGORY_TOOL, seq, eventId, null, null, null, null
        );
    }

    /**
     * A turn-finished event carrying token usage.
     */
    public static StreamEvent done(TokenUsage usage, int seq) {
        return done(usage, seq, null);
    }

    /**
     * A turn-finished event carrying token usage (with causal id).
     */
    public static StreamEvent done(TokenUsage usage, int seq, String eventId) {
        return new StreamEvent(
            "done", null, List.of(), usage, null,
            SOURCE_AGENT, CATEGORY_LIFECYCLE, seq, eventId, null, null, null, null
        );
    }

    /**
     * An error event.
     */
    public static StreamEvent error(String message, int seq) {
        return error(message, seq, null);
    }

    /**
     * An error event (with causal id).
     */
    public static StreamEvent error(String message, int seq, String eventId) {
        return new StreamEvent(
            "error", null, List.of(), new TokenUsage(), message,
            SOURCE_AGENT, CATEGORY_LIFECYCLE, seq, eventId, null, null, null, null
        );
    }

    /**
     * Goal loop started.
     */
    public static StreamEvent goalStart(String goalId, int seq, String goalDescription) {
        return new StreamEvent(
            "goal_start", goalDescription, List.of(), new TokenUsage(), null,
            SOURCE_GOAL_LOOP, CATEGORY_LIFECYCLE, seq, goalId, null, null, null, null
        );
    }

    /**
     * Goal loop iteration completed.
     */
    public static StreamEvent goalIteration(String iterId, String goalId, int seq, int iteration, String text) {
        return new StreamEvent(
            "goal_iteration", text, List.of(), new TokenUsage(), null,
            SOURCE_GOAL_LOOP, CATEGORY_LIFECYCLE, seq, iterId, goalId, iteration, null, null
        );
    }

    /**
     * Goal loop verification result.
     */
    public static StreamEvent goalVerification(String verifyId, String iterId, int seq, boolean achieved, String reasoning) {
        return new StreamEvent(
            "goal_verification", reasoning, List.of(), new TokenUsage(), null,
            SOURCE_GOAL_LOOP, CATEGORY_VERIFICATION, seq, verifyId, iterId, null, achieved, null
        );
    }

    /**
     * Goal loop finished, carrying the {@link com.harness.loop.types.GoalResult}.
     * The result is passed as {@code Object} to avoid a core&rarr;loop dependency.
     */
    public static StreamEvent goalDone(String doneId, String goalId, int seq, Object goalResult, boolean achieved, String error) {
        return new StreamEvent(
            "goal_done", null, List.of(), new TokenUsage(), error,
            SOURCE_GOAL_LOOP, CATEGORY_LIFECYCLE, seq, doneId, goalId, null, achieved, goalResult
        );
    }

    /**
     * Whether this is a goal-loop lifecycle event.
     */
    public boolean isGoalEvent() {
        return type != null && type.startsWith("goal_");
    }

    @Override
    public String toString() {
        StringBuilder sb = new StringBuilder();
        sb.append("StreamEvent{");
        sb.append("type=").append(type);
        sb.append(", source=").append(source);
        sb.append(", category=").append(category);
        sb.append(", seq=").append(seq);
        if (eventId != null) sb.append(", eventId=").append(eventId);
        if (parentId != null) sb.append(", parentId=").append(parentId);
        if (text != null) sb.append(", text='").append(truncate(text, 60)).append('\'');
        if (error != null) sb.append(", error='").append(error).append('\'');
        if (iteration != null) sb.append(", iteration=").append(iteration);
        if (achieved != null) sb.append(", achieved=").append(achieved);
        sb.append('}');
        return sb.toString();
    }

    private static String truncate(String s, int max) {
        return s.length() <= max ? s : s.substring(0, max) + "...";
    }
}
