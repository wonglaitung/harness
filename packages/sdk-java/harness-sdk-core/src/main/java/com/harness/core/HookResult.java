package com.harness.core;

import java.util.Map;

import com.harness.types.Message;
import com.harness.types.ToolResult;

/**
 * Result returned by a hook.
 *
 * Controls what happens after the hook executes.
 *
 * @param action What action to take
 * @param modifiedArgs New arguments (for MODIFY_ARGS)
 * @param modifiedResult New result (for MODIFY_RESULT)
 * @param injectMessage Message to add to context (for INJECT_MESSAGE)
 * @param delaySeconds Delay before retry (for RETRY)
 * @param clearContext Whether to clear context (for Ralph Loop)
 * @param metadata Additional data (e.g., abort reason)
 */
public record HookResult(
    HookAction action,
    Map<String, Object> modifiedArgs,
    ToolResult modifiedResult,
    Message injectMessage,
    double delaySeconds,
    boolean clearContext,
    Map<String, Object> metadata
) {

    /**
     * Create a continue result.
     */
    public static HookResult continue_() {
        return new HookResult(HookAction.CONTINUE, null, null, null, 0, false, Map.of());
    }

    /**
     * Create an abort result.
     */
    public static HookResult abort(String reason) {
        return new HookResult(HookAction.ABORT, null, null, null, 0, false, Map.of("reason", reason));
    }

    /**
     * Create an abort result with metadata.
     */
    public static HookResult abort(String reason, Map<String, Object> metadata) {
        Map<String, Object> merged = new java.util.HashMap<>(metadata);
        merged.put("reason", reason);
        return new HookResult(HookAction.ABORT, null, null, null, 0, false, merged);
    }

    /**
     * Create a retry result.
     */
    public static HookResult retry(double delaySeconds) {
        return new HookResult(HookAction.RETRY, null, null, null, delaySeconds, false, Map.of());
    }

    /**
     * Create an inject message result.
     */
    public static HookResult injectMessage(Message message) {
        return new HookResult(HookAction.INJECT_MESSAGE, null, null, message, 0, false, Map.of());
    }

    /**
     * Create a modify args result.
     */
    public static HookResult modifyArgs(Map<String, Object> newArgs) {
        return new HookResult(HookAction.MODIFY_ARGS, newArgs, null, null, 0, false, Map.of());
    }

    /**
     * Create a modify result result.
     */
    public static HookResult modifyResult(ToolResult newResult) {
        return new HookResult(HookAction.MODIFY_RESULT, null, newResult, null, 0, false, Map.of());
    }

    /**
     * Create a modify tool output result (shorthand for string output).
     */
    public static HookResult modifyToolOutput(String newOutput) {
        return new HookResult(
            HookAction.MODIFY_RESULT,
            null,
            new ToolResult("", true, newOutput, null),
            null, 0, false, Map.of()
        );
    }

    /**
     * Create a reinject result (for Ralph Loop).
     */
    public static HookResult reinject(boolean clearContext) {
        return new HookResult(HookAction.REINJECT, null, null, null, 0, clearContext, Map.of());
    }

    /**
     * Create builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private HookAction action = HookAction.CONTINUE;
        private Map<String, Object> modifiedArgs = null;
        private ToolResult modifiedResult = null;
        private Message injectMessage = null;
        private double delaySeconds = 0;
        private boolean clearContext = false;
        private Map<String, Object> metadata = Map.of();

        public Builder action(HookAction action) {
            this.action = action;
            return this;
        }

        public Builder modifiedArgs(Map<String, Object> modifiedArgs) {
            this.modifiedArgs = modifiedArgs;
            return this;
        }

        public Builder modifiedResult(ToolResult modifiedResult) {
            this.modifiedResult = modifiedResult;
            return this;
        }

        public Builder injectMessage(Message injectMessage) {
            this.injectMessage = injectMessage;
            return this;
        }

        public Builder delaySeconds(double delaySeconds) {
            this.delaySeconds = delaySeconds;
            return this;
        }

        public Builder clearContext(boolean clearContext) {
            this.clearContext = clearContext;
            return this;
        }

        public Builder metadata(Map<String, Object> metadata) {
            this.metadata = metadata;
            return this;
        }

        public HookResult build() {
            return new HookResult(action, modifiedArgs, modifiedResult, injectMessage, delaySeconds, clearContext, metadata);
        }
    }
}
