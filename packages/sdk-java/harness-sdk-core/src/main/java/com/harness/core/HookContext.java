package com.harness.core;

import java.util.List;
import java.util.Map;

import com.harness.types.LLMResponse;
import com.harness.types.Message;
import com.harness.types.ToolResult;

/**
 * Context passed to hooks during execution.
 *
 * Contains all relevant information about the current state
 * of the agent loop at the hook point.
 *
 * @param hookPoint Which hook point triggered this
 * @param sessionId Current session ID
 * @param iteration Current iteration number
 * @param toolName Tool name (for tool hooks)
 * @param toolArgs Tool arguments (for BEFORE_TOOL_EXECUTE)
 * @param toolResult Tool result (for AFTER_TOOL_EXECUTE)
 * @param llmResponse LLM response (for AFTER_LLM_CALL)
 * @param error Exception (for ON_ERROR)
 * @param messages Current messages (optional)
 * @param metadata Additional context data
 */
public record HookContext(
    HookPoint hookPoint,
    String sessionId,
    int iteration,
    String toolName,
    Map<String, Object> toolArgs,
    ToolResult toolResult,
    LLMResponse llmResponse,
    Exception error,
    List<Message> messages,
    Map<String, Object> metadata
) {

    /**
     * Create builder.
     */
    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private HookPoint hookPoint;
        private String sessionId;
        private int iteration = 0;
        private String toolName = null;
        private Map<String, Object> toolArgs = null;
        private ToolResult toolResult = null;
        private LLMResponse llmResponse = null;
        private Exception error = null;
        private List<Message> messages = null;
        private Map<String, Object> metadata = Map.of();

        public Builder hookPoint(HookPoint hookPoint) {
            this.hookPoint = hookPoint;
            return this;
        }

        public Builder sessionId(String sessionId) {
            this.sessionId = sessionId;
            return this;
        }

        public Builder iteration(int iteration) {
            this.iteration = iteration;
            return this;
        }

        public Builder toolName(String toolName) {
            this.toolName = toolName;
            return this;
        }

        public Builder toolArgs(Map<String, Object> toolArgs) {
            this.toolArgs = toolArgs;
            return this;
        }

        public Builder toolResult(ToolResult toolResult) {
            this.toolResult = toolResult;
            return this;
        }

        public Builder llmResponse(LLMResponse llmResponse) {
            this.llmResponse = llmResponse;
            return this;
        }

        public Builder error(Exception error) {
            this.error = error;
            return this;
        }

        public Builder messages(List<Message> messages) {
            this.messages = messages;
            return this;
        }

        public Builder metadata(Map<String, Object> metadata) {
            this.metadata = metadata;
            return this;
        }

        public HookContext build() {
            return new HookContext(
                hookPoint, sessionId, iteration, toolName, toolArgs,
                toolResult, llmResponse, error, messages, metadata
            );
        }
    }
}
