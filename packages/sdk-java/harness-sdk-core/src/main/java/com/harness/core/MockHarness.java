package com.harness.core;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

import com.harness.types.LLMResponse;
import com.harness.types.Message;
import com.harness.types.Session;
import com.harness.types.StopReason;
import com.harness.types.TokenUsage;
import com.harness.types.ToolCall;

/**
 * Mock Harness for testing.
 *
 * Provides a fully mocked agent harness for unit testing without real LLM calls.
 * Supports:
 * - Predefined responses
 * - Automatic tool result handling
 * - Deterministic testing
 *
 * Example:
 * <pre>
 * MockHarness mock = new MockHarness();
 * mock.addResponse(MockResponse.text("Hello!"));
 *
 * LoopResult result = mock.run("Say hello").join();
 * assert result.finalResponse().equals("Hello!");
 * </pre>
 */
public class MockHarness {

    private final List<MockResponse> responses = new ArrayList<>();
    private final Map<String, String> toolResults = new HashMap<>();
    private int responseIndex = 0;
    private int totalIterations = 0;

    public MockHarness() {
    }

    public MockHarness(List<MockResponse> responses) {
        this.responses.addAll(responses);
    }

    /**
     * Add a mock response.
     */
    public void addResponse(MockResponse response) {
        responses.add(response);
    }

    /**
     * Add automatic tool result for a tool.
     */
    public void addToolResult(String toolName, String result) {
        toolResults.put(toolName, result);
    }

    /**
     * Set all responses.
     */
    public void setResponses(List<MockResponse> responses) {
        this.responses.clear();
        this.responses.addAll(responses);
        this.responseIndex = 0;
    }

    /**
     * Run the mock harness.
     */
    public CompletableFuture<MockLoopResult> run(String prompt) {
        return run(prompt, "mock-session", 10);
    }

    /**
     * Run the mock harness.
     */
    public CompletableFuture<MockLoopResult> run(String prompt, String sessionId, int maxIterations) {
        return CompletableFuture.supplyAsync(() -> {
            responseIndex = 0;
            List<Message> messages = new ArrayList<>();
            messages.add(Message.user(prompt));

            int iteration = 0;
            int totalInputTokens = 0;
            int totalOutputTokens = 0;

            while (iteration < maxIterations && responseIndex < responses.size()) {
                MockResponse mockResponse = responses.get(responseIndex);
                responseIndex++;

                totalInputTokens += mockResponse.inputTokens();
                totalOutputTokens += mockResponse.outputTokens();

                // Add assistant message
                if (mockResponse.content() != null && !mockResponse.content().isEmpty()) {
                    messages.add(Message.assistant(mockResponse.content()));
                }

                // Handle tool calls
                if (mockResponse.isToolUse()) {
                    for (ToolCall toolCall : mockResponse.toolCalls()) {
                        String resultContent = toolResults.getOrDefault(
                            toolCall.name(),
                            "Mock result for " + toolCall.name()
                        );

                        messages.add(Message.tool(resultContent, toolCall.id(), toolCall.name()));
                    }
                    iteration++;
                    continue;
                }

                // Done
                totalIterations = iteration;
                return new MockLoopResult(
                    true,
                    messages,
                    mockResponse.content(),
                    iteration,
                    new TokenUsage(totalInputTokens, totalOutputTokens)
                );
            }

            // Max iterations reached or responses exhausted
            return new MockLoopResult(
                false,
                messages,
                responses.isEmpty() ? "" : responses.get(responses.size() - 1).content(),
                iteration,
                new TokenUsage(totalInputTokens, totalOutputTokens)
            );
        });
    }

    /**
     * Reset mock state.
     */
    public void reset() {
        responseIndex = 0;
        totalIterations = 0;
        responses.clear();
        toolResults.clear();
    }

    /**
     * Get current response index.
     */
    public int currentResponseIndex() {
        return responseIndex;
    }

    /**
     * Get number of responses remaining.
     */
    public int responsesRemaining() {
        return responses.size() - responseIndex;
    }

    /**
     * Mock loop result.
     */
    public record MockLoopResult(
        boolean success,
        List<Message> messages,
        String finalResponse,
        int iterations,
        TokenUsage tokenUsage
    ) {}
}
