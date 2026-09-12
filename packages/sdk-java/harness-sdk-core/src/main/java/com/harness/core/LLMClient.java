package com.harness.core;

import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.function.Consumer;

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
     * Stream the LLM response as structured {@link StreamEvent}s.
     *
     * <p>Default implementation delegates to {@link #stream} and wraps each raw
     * text chunk into a {@code StreamEvent} of type {@code "text"}. Concrete
     * providers may override this to also emit {@code tool_calls}/{@code done}
     * events with usage. The {@code seq} is left at 0 by the default wrapper;
     * callers that need a strict sequence should manage it themselves.</p>
     *
     * @param messages The conversation messages
     * @param tools Available tools (optional)
     * @param systemPrompt System prompt (optional)
     * @param onEvent Callback for each structured event
     */
    default void streamWithEvents(
            List<Message> messages,
            List<ToolDefinition> tools,
            String systemPrompt,
            java.util.function.Consumer<StreamEvent> onEvent) {
        stream(messages, tools, systemPrompt, chunk -> {
            if (chunk != null && !chunk.isEmpty()) {
                onEvent.accept(StreamEvent.textChunk(chunk, 0));
            }
        });
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