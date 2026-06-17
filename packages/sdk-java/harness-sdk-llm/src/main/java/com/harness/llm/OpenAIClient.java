package com.harness.llm;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.openai.client.OpenAIClient;
import com.openai.client.okhttp.OpenAIOkHttpClient;
import com.openai.models.chat.completions.*;

import com.harness.core.LLMClient;
import com.harness.types.LLMResponse;
import com.harness.types.Message;
import com.harness.types.StopReason;
import com.harness.types.ToolCall;
import com.harness.types.TokenUsage;

/**
 * OpenAI-compatible API client.
 *
 * Wraps the official OpenAI Java SDK. Supports custom base URL
 * for third-party API gateways (bank environments).
 */
public class OpenAIClient implements LLMClient {

    private static final Logger logger = LoggerFactory.getLogger(OpenAIClient.class);

    private final OpenAIClient client;
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

        // Build message list
        List<ChatCompletionMessageParam> messageParams = new ArrayList<>();

        // Add system prompt
        if (systemPrompt != null && !systemPrompt.isEmpty()) {
            messageParams.add(ChatCompletionSystemMessageParam.builder()
                .content(systemPrompt)
                .build());
        }

        // Add messages
        for (Message msg : messages) {
            switch (msg.role()) {
                case "user" -> messageParams.add(ChatCompletionUserMessageParam.builder()
                    .content(msg.contentAsString())
                    .build());
                case "assistant" -> messageParams.add(ChatCompletionAssistantMessageParam.builder()
                    .content(msg.contentAsString())
                    .build());
                case "tool" -> {
                    Map<String, Object> metadata = msg.metadata();
                    String toolCallId = metadata.containsKey("tool_call_id") ?
                        (String) metadata.get("tool_call_id") : "";
                    messageParams.add(ChatCompletionToolMessageParam.builder()
                        .toolCallId(toolCallId)
                        .content(msg.contentAsString())
                        .build());
                }
                default -> logger.warn("Unknown message role: {}", msg.role());
            }
        }

        // Build request
        ChatCompletionCreateParams.Builder paramsBuilder = ChatCompletionCreateParams.builder()
            .model(modelName)
            .messages(messageParams);

        // Add tools if present
        if (tools != null && !tools.isEmpty()) {
            List<ChatCompletionTool> chatTools = new ArrayList<>();
            for (ToolDefinition tool : tools) {
                chatTools.add(ChatCompletionTool.builder()
                    .type(ChatCompletionToolType.FUNCTION)
                    .function(ChatCompletionFunction.builder()
                        .name(tool.name())
                        .description(tool.description())
                        .parameters(tool.inputSchema())
                        .build())
                    .build());
            }
            paramsBuilder.tools(chatTools);
        }

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
        // Build message list
        List<ChatCompletionMessageParam> messageParams = new ArrayList<>();

        if (systemPrompt != null && !systemPrompt.isEmpty()) {
            messageParams.add(ChatCompletionSystemMessageParam.builder()
                .content(systemPrompt)
                .build());
        }

        for (Message msg : messages) {
            switch (msg.role()) {
                case "user" -> messageParams.add(ChatCompletionUserMessageParam.builder()
                    .content(msg.contentAsString())
                    .build());
                case "assistant" -> messageParams.add(ChatCompletionAssistantMessageParam.builder()
                    .content(msg.contentAsString())
                    .build());
                default -> {}
            }
        }

        ChatCompletionCreateParams params = ChatCompletionCreateParams.builder()
            .model(modelName)
            .messages(messageParams)
            .build();

        // Stream response
        client.chat().completions().createStreaming(params)
            .subscribe(chunk -> {
                if (chunk.choices() != null && !chunk.choices().isEmpty()) {
                    ChatCompletionChunk.Choice choice = chunk.choices().get(0);
                    if (choice.delta() != null && choice.delta().content() != null) {
                        onChunk.onChunk(choice.delta().content());
                    }
                }
            });
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

        String content = message.content() != null ? message.content() : "";
        List<ToolCall> toolCalls = new ArrayList<>();

        // Extract tool calls
        if (message.toolCalls() != null) {
            for (ChatCompletionMessageToolCall toolCall : message.toolCalls()) {
                toolCalls.add(new ToolCall(
                    toolCall.id(),
                    toolCall.function().name(),
                    parseJsonArguments(toolCall.function().arguments())
                ));
            }
        }

        // Determine stop reason
        StopReason stopReason = StopReason.END_TURN;
        if (choice.finishReason() != null) {
            switch (choice.finishReason()) {
                case ChatCompletionFinishReason.STOP -> stopReason = StopReason.END_TURN;
                case ChatCompletionFinishReason.TOOL_CALLS -> stopReason = StopReason.TOOL_USE;
                case ChatCompletionFinishReason.LENGTH -> stopReason = StopReason.MAX_TOKENS;
                default -> stopReason = StopReason.END_TURN;
            }
        }

        // Extract usage
        TokenUsage usage = new TokenUsage();
        if (completion.usage() != null) {
            usage = new TokenUsage(
                completion.usage().promptTokens() != null ? completion.usage().promptTokens() : 0,
                completion.usage().completionTokens() != null ? completion.usage().completionTokens() : 0
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
            // Simple parsing - use Jackson in production
            return Map.of(); // Placeholder
        } catch (Exception e) {
            logger.warn("Failed to parse tool arguments: {}", json);
            return Map.of();
        }
    }
}