package com.harness.core;

import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

import com.harness.types.LLMResponse;
import com.harness.types.Message;

/**
 * LLM client interface.
 *
 * All LLM providers (Anthropic, OpenAI, etc.) must implement this interface.
 */
public interface LLMClient {

    /**
     * Get the model name.
     */
    String modelName();

    /**
     * Call the LLM synchronously.
     *
     * @param messages The conversation messages
     * @param tools Available tools (optional)
     * @param systemPrompt System prompt (optional)
     * @return The LLM response
     */
    LLMResponse call(List<Message> messages, List<ToolDefinition> tools, String systemPrompt);

    /**
     * Call the LLM asynchronously.
     *
     * @param messages The conversation messages
     * @param tools Available tools (optional)
     * @param systemPrompt System prompt (optional)
     * @return A future containing the LLM response
     */
    CompletableFuture<LLMResponse> callAsync(List<Message> messages, List<ToolDefinition> tools, String systemPrompt);

    /**
     * Stream the LLM response.
     *
     * @param messages The conversation messages
     * @param tools Available tools (optional)
     * @param systemPrompt System prompt (optional)
     * @param onChunk Callback for each chunk
     */
    void stream(List<Message> messages, List<ToolDefinition> tools, String systemPrompt, StreamCallback onChunk);

    /**
     * Stream callback interface.
     */
    @FunctionalInterface
    interface StreamCallback {
        void onChunk(String chunk);
    }

    /**
     * Tool definition for LLM function calling.
     */
    record ToolDefinition(
        String name,
        String description,
        Map<String, Object> inputSchema
    ) {
        public static ToolDefinition of(String name, String description, Map<String, Object> inputSchema) {
            return new ToolDefinition(name, description, inputSchema);
        }
    }
}