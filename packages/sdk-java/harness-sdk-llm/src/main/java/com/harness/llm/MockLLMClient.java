package com.harness.llm;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

import com.harness.core.LLMClient;
import com.harness.types.LLMResponse;
import com.harness.types.Message;
import com.harness.types.StopReason;
import com.harness.types.TokenUsage;
import com.harness.types.ToolCall;

/**
 * Mock LLM client for testing.
 *
 * This client returns predefined responses without making real API calls.
 * Useful for unit tests and development.
 *
 * Example:
 * <pre>
 * MockLLMClient client = new MockLLMClient();
 * client.addResponse(MockResponse.text("Hello, world!"));
 *
 * LLMResponse response = client.call(messages, null, null);
 * // response.content() == "Hello, world!"
 * </pre>
 */
public class MockLLMClient implements LLMClient {

    private final String modelName;
    private final List<MockResponse> responses = new ArrayList<>();
    private int responseIndex = 0;
    private int callCount = 0;
    private List<Message> lastMessages = null;
    private List<ToolDefinition> lastTools = null;

    public MockLLMClient() {
        this("mock-model");
    }

    public MockLLMClient(String modelName) {
        this.modelName = modelName;
    }

    /**
     * Set predefined responses.
     */
    public void setResponses(List<MockResponse> responses) {
        this.responses.clear();
        this.responses.addAll(responses);
        this.responseIndex = 0;
    }

    /**
     * Add a response to the queue.
     */
    public void addResponse(MockResponse response) {
        responses.add(response);
    }

    /**
     * Get number of calls made.
     */
    public int getCallCount() {
        return callCount;
    }

    /**
     * Get last messages sent to the client.
     */
    public List<Message> getLastMessages() {
        return lastMessages;
    }

    /**
     * Get last tools sent to the client.
     */
    public List<ToolDefinition> getLastTools() {
        return lastTools;
    }

    @Override
    public String modelName() {
        return modelName;
    }

    @Override
    public LLMResponse call(List<Message> messages, List<ToolDefinition> tools, String systemPrompt) {
        callCount++;
        lastMessages = messages;
        lastTools = tools;

        // Get next predefined response or create a default one
        MockResponse mock;
        if (responseIndex < responses.size()) {
            mock = responses.get(responseIndex);
            responseIndex++;
        } else {
            // Default response
            mock = MockResponse.text("This is a mock response.");
        }

        // Convert mock response to LLMResponse
        List<ToolCall> toolCalls = new ArrayList<>();
        for (Map<String, Object> tc : mock.getToolCalls()) {
            String id = (String) tc.getOrDefault("id", "mock_tool_" + toolCalls.size());
            String name = (String) tc.getOrDefault("name", "unknown");
            @SuppressWarnings("unchecked")
            Map<String, Object> arguments = (Map<String, Object>) tc.getOrDefault("arguments", new HashMap<>());
            toolCalls.add(new ToolCall(id, name, arguments));
        }

        // Estimate tokens
        int inputTokens = estimateTokens(messages);
        int outputTokens = mock.getContent() != null ? mock.getContent().length() / 4 : 0;

        return LLMResponse.builder()
            .content(mock.getContent())
            .toolCalls(toolCalls)
            .stopReason(mock.getStopReason())
            .usage(new TokenUsage(inputTokens, outputTokens))
            .build();
    }

    @Override
    public CompletableFuture<LLMResponse> callAsync(List<Message> messages, List<ToolDefinition> tools, String systemPrompt) {
        return CompletableFuture.supplyAsync(() -> call(messages, tools, systemPrompt));
    }

    @Override
    public void stream(List<Message> messages, List<ToolDefinition> tools, String systemPrompt, StreamCallback onChunk) {
        // Get response content
        LLMResponse response = call(messages, tools, systemPrompt);

        // Stream in chunks
        if (response.content() != null) {
            String[] words = response.content().split(" ");
            for (int i = 0; i < words.length; i++) {
                String chunk = i == 0 ? words[i] : " " + words[i];
                if (onChunk != null) {
                    onChunk.onChunk(chunk);
                }
            }
        }
    }

    /**
     * Reset the mock client state.
     */
    public void reset() {
        responseIndex = 0;
        callCount = 0;
        lastMessages = null;
        lastTools = null;
    }

    /**
     * Clear all responses.
     */
    public void clear() {
        responses.clear();
        reset();
    }

    private int estimateTokens(List<Message> messages) {
        if (messages == null) return 100;
        int total = 0;
        for (Message msg : messages) {
            String content = msg.contentAsString();
            if (content != null) {
                total += content.length() / 4;
            }
        }
        return Math.max(100, total);
    }

    /**
     * Helper to create mock responses that simulate tool use.
     *
     * @param toolName Name of the tool to call
     * @param toolArgs Arguments for the tool
     * @param finalResponse Response after tool execution
     * @return List of MockResponse objects
     */
    public static List<MockResponse> createToolUseSequence(
        String toolName,
        Map<String, Object> toolArgs,
        String finalResponse
    ) {
        List<MockResponse> sequence = new ArrayList<>();

        // First response: tool call
        sequence.add(MockResponse.builder()
            .content("")
            .addToolCall("mock_tool_call_1", toolName, toolArgs)
            .stopReason(StopReason.TOOL_USE)
            .build());

        // Second response: final answer
        sequence.add(MockResponse.text(finalResponse));

        return sequence;
    }
}
