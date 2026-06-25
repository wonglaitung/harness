package com.harness.core;

import java.util.List;

/**
 * Base interface for lifecycle hooks.
 *
 * Hooks are called at specific points in the agent loop.
 * Implementations define custom behavior by implementing execute().
 *
 * Example:
 * <pre>
 * public class MyHook implements LifecycleHook {
 *     &#64;Override
 *     public List&lt;HookPoint&gt; hookPoints() {
 *         return List.of(HookPoint.BEFORE_TOOL_EXECUTE);
 *     }
 *
 *     &#64;Override
 *     public HookResult execute(HookContext context) {
 *         if ("dangerous_tool".equals(context.toolName())) {
 *             return HookResult.abort("Dangerous tool blocked");
 *         }
 *         return HookResult.continue_();
 *     }
 * }
 *
 * // Register with agent
 * agent.addHook(new MyHook());
 * </pre>
 */
public interface LifecycleHook {

    /**
     * Which hook points this hook subscribes to.
     *
     * Override to specify which points to hook into.
     */
    default List<HookPoint> hookPoints() {
        return List.of();
    }

    /**
     * Execute the hook logic.
     *
     * @param context Context about the current state
     * @return HookResult controlling what happens next
     */
    HookResult execute(HookContext context);

    /**
     * Reset hook state (called when session ends).
     */
    default void reset() {
        // Default: no-op
    }

    /**
     * Reset hook state for a specific session.
     */
    default void reset(String sessionId) {
        // Default: no-op
    }
}
