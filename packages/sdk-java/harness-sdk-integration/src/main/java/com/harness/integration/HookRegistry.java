package com.harness.integration;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.core.HookAction;
import com.harness.core.HookContext;
import com.harness.core.HookPoint;
import com.harness.core.HookResult;
import com.harness.core.LifecycleHook;

/**
 * Registry for lifecycle hooks.
 *
 * Manages hook registration and execution at specific points in the agent loop.
 * Thread-safe for concurrent access.
 *
 * Example:
 * <pre>
 * HookRegistry registry = new HookRegistry();
 *
 * // Register a hook
 * registry.register(new MyHook());
 *
 * // Execute hooks at a point
 * List<HookResult> results = registry.execute(HookPoint.BEFORE_TOOL_EXECUTE, context);
 * </pre>
 */
public class HookRegistry {

    private static final Logger logger = LoggerFactory.getLogger(HookRegistry.class);

    // Map of hook point to list of hooks interested in that point
    private final Map<HookPoint, List<LifecycleHook>> hooksByPoint = new ConcurrentHashMap<>();

    // All registered hooks (for reset operations)
    private final List<LifecycleHook> allHooks = new ArrayList<>();

    /**
     * Register a lifecycle hook.
     *
     * @param hook The hook to register
     */
    public synchronized void register(LifecycleHook hook) {
        if (hook == null) {
            return;
        }

        allHooks.add(hook);

        // Register for each hook point the hook is interested in
        for (HookPoint point : hook.hookPoints()) {
            hooksByPoint.computeIfAbsent(point, k -> new ArrayList<>()).add(hook);
        }

        logger.debug("Registered hook: {}", hook.getClass().getSimpleName());
    }

    /**
     * Unregister a lifecycle hook.
     *
     * @param hook The hook to unregister
     */
    public synchronized void unregister(LifecycleHook hook) {
        if (hook == null) {
            return;
        }

        allHooks.remove(hook);

        // Remove from all hook points
        for (List<LifecycleHook> hooks : hooksByPoint.values()) {
            hooks.remove(hook);
        }

        logger.debug("Unregistered hook: {}", hook.getClass().getSimpleName());
    }

    /**
     * Execute all hooks registered for a specific point.
     *
     * @param point The hook point
     * @param context The execution context
     * @return List of results from hooks that were executed
     */
    public List<HookResult> execute(HookPoint point, HookContext context) {
        List<HookResult> results = new ArrayList<>();
        List<LifecycleHook> hooks = hooksByPoint.get(point);

        if (hooks == null || hooks.isEmpty()) {
            return results;
        }

        for (LifecycleHook hook : hooks) {
            try {
                HookResult result = hook.execute(context);
                results.add(result);

                // If hook returns abort, stop execution
                if (result != null && result.action() == HookAction.ABORT) {
                    Object reason = result.metadata().get("reason");
                    logger.info("Hook {} requested abort: {}",
                        hook.getClass().getSimpleName(), reason);
                    break;
                }
            } catch (Exception e) {
                logger.error("Hook {} threw exception at {}",
                    hook.getClass().getSimpleName(), point, e);
                results.add(HookResult.abort(e.getMessage()));
            }
        }

        return results;
    }

    /**
     * Check if any hook at a point wants to abort.
     *
     * @param point The hook point
     * @param context The execution context
     * @return true if any hook wants to abort
     */
    public boolean shouldAbort(HookPoint point, HookContext context) {
        List<HookResult> results = execute(point, context);
        for (HookResult result : results) {
            if (result != null && result.action() == HookAction.ABORT) {
                return true;
            }
        }
        return false;
    }

    /**
     * Reset all hooks (clear session state).
     */
    public void reset() {
        for (LifecycleHook hook : allHooks) {
            try {
                hook.reset();
            } catch (Exception e) {
                logger.error("Failed to reset hook: {}", hook.getClass().getSimpleName(), e);
            }
        }
    }

    /**
     * Reset hooks for a specific session.
     *
     * @param sessionId The session ID
     */
    public void resetSession(String sessionId) {
        for (LifecycleHook hook : allHooks) {
            try {
                hook.reset(sessionId);
            } catch (Exception e) {
                logger.error("Failed to reset hook for session {}: {}",
                    sessionId, hook.getClass().getSimpleName(), e);
            }
        }
    }

    /**
     * Get all registered hooks.
     */
    public List<LifecycleHook> getAllHooks() {
        return new ArrayList<>(allHooks);
    }

    /**
     * Get hooks registered for a specific point.
     *
     * @param point The hook point
     * @return List of hooks for that point
     */
    public List<LifecycleHook> getHooksForPoint(HookPoint point) {
        List<LifecycleHook> hooks = hooksByPoint.get(point);
        return hooks != null ? new ArrayList<>(hooks) : List.of();
    }

    /**
     * Clear all registered hooks.
     */
    public synchronized void clear() {
        allHooks.clear();
        hooksByPoint.clear();
    }
}
