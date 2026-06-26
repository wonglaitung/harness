package com.harness.llm;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.openai.client.okhttp.OpenAIOkHttpClient;
import com.openai.models.chat.completions.*;
import com.openai.models.completions.CompletionUsage;

import com.harness.core.LLMClient;
import com.harness.types.LLMResponse;
import com.harness.types.Message;
import com.harness.types.StopReason;
import com.harness.types.TokenUsage;
import com.harness.types.ToolCall;

/**
 * OpenAI-compatible API client.
 *
 * Wraps the official OpenAI Java SDK. Supports custom base URL
 * for third-party API gateways (bank environments).
 */
public class OpenAIClient implements LLMClient {

    private static final Logger logger = LoggerFactory.getLogger(OpenAIClient.class);
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final com.openai.client.OpenAIClient client;
    private final String modelName;

    /**
     * Create client with API key.
     */
    public OpenAIClient(String apiKey, String modelName) {
        this.client = OpenAIOkHttpClient.builder()
            .apiKey(apiKey)
            .build();
        this.modelName = modelName;
    }

    /**
     * Create client with custom base URL (for bank API gateway).
     */
    public OpenAIClient(String apiKey, String baseUrl, String modelName) {
        this.client = OpenAIOkHttpClient.builder()
            .apiKey(apiKey)
            .baseUrl(baseUrl)
            .build();
        this.modelName = modelName;
    }

    /**
     * Create client from environment variables.
     */
    public OpenAIClient(String modelName) {
        this.client = OpenAIOkHttpClient.fromEnv();
        this.modelName = modelName;
    }

    @Override
    public String modelName() {
        return modelName;
    }

    @Override
    public LLMResponse call(List<Message> messages, List<ToolDefinition> tools, String systemPrompt) {
        logger.debug("Calling OpenAI-compatible API with {} messages", messages.size());

        // Build request using convenience methods
        ChatCompletionCreateParams.Builder paramsBuilder = ChatCompletionCreateParams.builder()
            .model(modelName);

        // Add system prompt
        if (systemPrompt != null && !systemPrompt.isEmpty()) {
            paramsBuilder.addSystemMessage(systemPrompt);
        }

        // Add messages
        for (Message msg : messages) {
            switch (msg.role()) {
                case "user" -> paramsBuilder.addUserMessage(msg.contentAsString());
                case "assistant" -> paramsBuilder.addAssistantMessage(msg.contentAsString());
                case "tool" -> {
                    Map<String, Object> metadata = msg.metadata();
                    String toolCallId = metadata.containsKey("tool_call_id") ?
                        (String) metadata.get("tool_call_id") : "";
                    // Use ChatCompletionToolMessageParam for tool messages
                    paramsBuilder.addMessage(
                        ChatCompletionToolMessageParam.builder()
                            .toolCallId(toolCallId)
                            .content(msg.contentAsString())
                            .build()
                    );
                }
                default -> logger.warn("Unknown message role: {}", msg.role());
            }
        }

        // Note: Tools are added via addTool(Class) for typed tools
        // For dynamic tools, we skip them in this simplified implementation

        ChatCompletionCreateParams params = paramsBuilder.build();

        // Make API call
        ChatCompletion completion = client.chat().completions().create(params);

        // Parse response
        return parseResponse(completion);
    }

    @Override
    public CompletableFuture<LLMResponse> callAsync(List<Message> messages, List<ToolDefinition> tools, String systemPrompt) {
        return CompletableFuture.supplyAsync(() -> call(messages, tools, systemPrompt));
    }

    @Override
    public void stream(List<Message> messages, List<ToolDefinition> tools, String systemPrompt, StreamCallback onChunk) {
        // Build request
        ChatCompletionCreateParams.Builder paramsBuilder = ChatCompletionCreateParams.builder()
            .model(modelName);

        if (systemPrompt != null && !systemPrompt.isEmpty()) {
            paramsBuilder.addSystemMessage(systemPrompt);
        }

        for (Message msg : messages) {
            switch (msg.role()) {
                case "user" -> paramsBuilder.addUserMessage(msg.contentAsString());
                case "assistant" -> paramsBuilder.addAssistantMessage(msg.contentAsString());
                default -> {}
            }
        }

        ChatCompletionCreateParams params = paramsBuilder.build();

        // Stream response - collect all chunks
        StringBuilder content = new StringBuilder();
        // Use stream() method for streaming
        try (var stream = client.chat().completions().createStreaming(params)) {
            stream.stream().forEach(chunk -> {
                if (chunk.choices() != null && !chunk.choices().isEmpty()) {
                    ChatCompletionChunk.Choice choice = chunk.choices().get(0);
                    if (choice.delta() != null && choice.delta().content().isPresent()) {
                        String text = choice.delta().content().get();
                        content.append(text);
                        if (onChunk != null) {
                            onChunk.onChunk(text);
                        }
                    }
                }
            });
        }
    }

    /**
     * Parse OpenAI response into LLMResponse.
     */
    private LLMResponse parseResponse(ChatCompletion completion) {
        if (completion.choices() == null || completion.choices().isEmpty()) {
            return new LLMResponse("");
        }

        ChatCompletion.Choice choice = completion.choices().get(0);
        ChatCompletionMessage message = choice.message();

        String content = message.content().orElse("");
        List<ToolCall> toolCalls = new ArrayList<>();

        // Extract tool calls
        if (message.toolCalls().isPresent()) {
            List<ChatCompletionMessageToolCall> calls = message.toolCalls().get();
            if (calls != null) {
                for (ChatCompletionMessageToolCall toolCall : calls) {
                    // ChatCompletionMessageToolCall is a union type, get function variant
                    toolCall.function().ifPresent(func -> {
                        String id = func.id();
                        ChatCompletionMessageFunctionToolCall.Function fn = func.function();
                        String name = fn.name();
                        String argsJson = fn.arguments();

                        toolCalls.add(new ToolCall(
                            id,
                            name,
                            parseJsonArguments(argsJson)
                        ));
                    });
                }
            }
        }

        // Determine stop reason from FinishReason
        StopReason stopReason = StopReason.END_TURN;
        ChatCompletion.Choice.FinishReason finishReason = choice.finishReason();
        if (finishReason != null) {
            // Compare with static instances
            if (finishReason == ChatCompletion.Choice.FinishReason.STOP) {
                stopReason = StopReason.END_TURN;
            } else if (finishReason == ChatCompletion.Choice.FinishReason.TOOL_CALLS) {
                stopReason = StopReason.TOOL_USE;
            } else if (finishReason == ChatCompletion.Choice.FinishReason.LENGTH) {
                stopReason = StopReason.MAX_TOKENS;
            }
        }

        // Extract usage - usage() returns Optional<CompletionUsage>
        TokenUsage usage = new TokenUsage();
        Optional<CompletionUsage> usageOpt = completion.usage();
        if (usageOpt.isPresent()) {
            CompletionUsage usageData = usageOpt.get();
            usage = new TokenUsage(
                (int) usageData.promptTokens(),
                (int) usageData.completionTokens()
            );
        }

        return LLMResponse.builder()
            .content(content)
            .toolCalls(toolCalls)
            .stopReason(stopReason)
            .usage(usage)
            .build();
    }

    /**
     * Parse JSON arguments string to Map.
     */
    private Map<String, Object> parseJsonArguments(String json) {
        if (json == null || json.isEmpty()) {
            return Map.of();
        }
        try {
            return MAPPER.readValue(json, new TypeReference<Map<String, Object>>() {});
        } catch (Exception e) {
            logger.warn("Failed to parse tool arguments: {}", json);
            return Map.of();
        }
    }
}
