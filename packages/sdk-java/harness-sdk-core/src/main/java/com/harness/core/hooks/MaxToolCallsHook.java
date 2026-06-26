package com.harness.core.hooks;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.core.HookContext;
import com.harness.core.HookPoint;
import com.harness.core.HookResult;
import com.harness.core.LifecycleHook;

/**
 * A hook that limits the number of calls to a specific tool.
 *
 * Useful to prevent infinite loops with a single tool.
 * Tracks call counts per session and aborts when limit is exceeded.
 *
 * Example:
 * <pre>
 * // Limit 'read' tool to 10 calls per session
 * agent.addHook(new MaxToolCallsHook("read", 10));
 *
 * // Limit 'bash' tool to 5 calls per session
 * agent.addHook(new MaxToolCallsHook("bash", 5));
 * </pre>
 */
public class MaxToolCallsHook implements LifecycleHook {

    private static final Logger logger = LoggerFactory.getLogger(MaxToolCallsHook.class);

    private final String toolName;
    private final int maxCalls;
    private final Map<String, AtomicInteger> callCounts = new ConcurrentHashMap<>();

    /**
     * Create a hook that limits calls to a specific tool.
     *
     * @param toolName The name of the tool to limit
     * @param maxCalls Maximum number of calls allowed per session
     */
    public MaxToolCallsHook(String toolName, int maxCalls) {
        this.toolName = toolName;
        this.maxCalls = maxCalls;
    }

    /**
     * Create a hook with default max calls (5).
     *
     * @param toolName The name of the tool to limit
     */
    public MaxToolCallsHook(String toolName) {
        this(toolName, 5);
    }

    @Override
    public List<HookPoint> hookPoints() {
        return List.of(HookPoint.BEFORE_TOOL_EXECUTE);
    }

    @Override
    public HookResult execute(HookContext context) {
        String currentToolName = context.toolName();

        // Only check for the configured tool
        if (!toolName.equals(currentToolName)) {
            return HookResult.continue_();
        }

        String sessionId = context.sessionId() != null ? context.sessionId() : "default";
        String key = sessionId + ":" + toolName;

        AtomicInteger count = callCounts.computeIfAbsent(key, k -> new AtomicInteger(0));
        int newCount = count.incrementAndGet();

        if (newCount > maxCalls) {
            logger.warn(
                "Tool {} called {} times in session {}, exceeds limit of {}",
                toolName, newCount, sessionId, maxCalls
            );
            return HookResult.abort(
                "Tool '" + toolName + "' exceeded max calls (" + maxCalls + ") in session"
            );
        }

        logger.debug("Tool {} call count: {}/{}", toolName, newCount, maxCalls);
        return HookResult.continue_();
    }

    @Override
    public void reset() {
        callCounts.clear();
        logger.debug("All call counts cleared");
    }

    @Override
    public void reset(String sessionId) {
        if (sessionId == null) {
            reset();
            return;
        }

        // Remove all keys for this session
        String prefix = sessionId + ":";
        callCounts.keySet().removeIf(key -> key.startsWith(prefix));
        logger.debug("Call counts cleared for session: {}", sessionId);
    }

    /**
     * Get the current call count for a session.
     *
     * @param sessionId Session ID
     * @return Current call count for the tool in this session
     */
    public int getCallCount(String sessionId) {
        String key = sessionId + ":" + toolName;
        AtomicInteger count = callCounts.get(key);
        return count != null ? count.get() : 0;
    }

    /**
     * Get the tool name being limited.
     */
    public String toolName() {
        return toolName;
    }

    /**
     * Get the maximum calls allowed.
     */
    public int maxCalls() {
        return maxCalls;
    }

    @Override
    public String toString() {
        return "MaxToolCallsHook{toolName='" + toolName + "', maxCalls=" + maxCalls + "}";
    }
}
