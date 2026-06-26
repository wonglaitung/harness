package com.harness.core.hooks;

import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.core.HookContext;
import com.harness.core.HookPoint;
import com.harness.core.HookResult;
import com.harness.core.LifecycleHook;

/**
 * A hook that logs all hook point events.
 *
 * Useful for debugging and monitoring agent behavior.
 * Logs include session ID, iteration, and relevant context.
 *
 * Example:
 * <pre>
 * agent.addHook(new LoggingHook());
 * </pre>
 */
public class LoggingHook implements LifecycleHook {

    private static final Logger logger = LoggerFactory.getLogger(LoggingHook.class);

    private final boolean verbose;

    /**
     * Create a logging hook with default verbosity.
     */
    public LoggingHook() {
        this(false);
    }

    /**
     * Create a logging hook with specified verbosity.
     *
     * @param verbose If true, logs more details including arguments
     */
    public LoggingHook(boolean verbose) {
        this.verbose = verbose;
    }

    @Override
    public List<HookPoint> hookPoints() {
        return List.of(HookPoint.values());
    }

    @Override
    public HookResult execute(HookContext context) {
        StringBuilder sb = new StringBuilder();
        sb.append("[Hook] ").append(context.hookPoint().name());
        sb.append(" session=").append(context.sessionId());
        sb.append(" iteration=").append(context.iteration());

        // Add context-specific information
        switch (context.hookPoint()) {
            case BEFORE_TOOL_EXECUTE, AFTER_TOOL_EXECUTE -> {
                if (context.toolName() != null) {
                    sb.append(" tool=").append(context.toolName());
                }
                if (verbose && context.toolArgs() != null && !context.toolArgs().isEmpty()) {
                    sb.append(" args=").append(context.toolArgs().keySet());
                }
                if (context.hookPoint() == HookPoint.AFTER_TOOL_EXECUTE && context.toolResult() != null) {
                    sb.append(" success=").append(context.toolResult().success());
                }
            }
            case AFTER_LLM_CALL -> {
                if (context.llmResponse() != null) {
                    sb.append(" stopReason=").append(context.llmResponse().stopReason());
                    if (verbose && context.llmResponse().usage() != null) {
                        sb.append(" tokens=").append(context.llmResponse().usage().inputTokens())
                          .append("/").append(context.llmResponse().usage().outputTokens());
                    }
                }
            }
            case ON_ERROR -> {
                if (context.error() != null) {
                    sb.append(" error=").append(context.error().getMessage());
                }
            }
            default -> {
                // No additional context
            }
        }

        logger.info(sb.toString());
        return HookResult.continue_();
    }

    @Override
    public String toString() {
        return "LoggingHook{verbose=" + verbose + "}";
    }
}
