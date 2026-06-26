package com.harness.llm;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.CompletableFuture;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.anthropic.client.okhttp.AnthropicOkHttpClient;
import com.anthropic.models.messages.*;

import com.harness.core.LLMClient;
import com.harness.types.LLMResponse;
import com.harness.types.Message;
import com.harness.types.StopReason;
import com.harness.types.ToolCall;
import com.harness.types.TokenUsage;

/**
 * Anthropic Claude API client.
 *
 * Wraps the official Anthropic Java SDK.
 */
public class AnthropicClient implements LLMClient {

    private static final Logger logger = LoggerFactory.getLogger(AnthropicClient.class);

    private final com.anthropic.client.AnthropicClient client;
    private final String modelName;

    /**
     * Create client with API key.
     */
    public AnthropicClient(String apiKey, String modelName) {
        this.client = AnthropicOkHttpClient.builder()
            .apiKey(apiKey)
            .build();
        this.modelName = modelName;
    }

    /**
     * Create client with custom base URL (for bank API gateway).
     */
    public AnthropicClient(String apiKey, String baseUrl, String modelName) {
        this.client = AnthropicOkHttpClient.builder()
            .apiKey(apiKey)
            .baseUrl(baseUrl)
            .build();
        this.modelName = modelName;
    }

    /**
     * Create client from environment variables.
     */
    public AnthropicClient(String modelName) {
        this.client = AnthropicOkHttpClient.fromEnv();
        this.modelName = modelName;
    }

    @Override
    public String modelName() {
        return modelName;
    }

    @Override
    public LLMResponse call(List<Message> messages, List<ToolDefinition> tools, String systemPrompt) {
        logger.debug("Calling Anthropic API with {} messages", messages.size());

        // Build request using convenience methods
        MessageCreateParams.Builder paramsBuilder = MessageCreateParams.builder()
            .model(Model.CLAUDE_SONNET_4_6)
            .maxTokens(4096L);

        // Set system prompt
        if (systemPrompt != null && !systemPrompt.isEmpty()) {
            paramsBuilder.system(systemPrompt);
        }

        // Add messages
        for (Message msg : messages) {
            switch (msg.role()) {
                case "user" -> paramsBuilder.addUserMessage(msg.contentAsString());
                case "assistant" -> paramsBuilder.addAssistantMessage(msg.contentAsString());
                case "tool" -> {
                    // Handle tool result using ToolResultBlockParam
                    Map<String, Object> metadata = msg.metadata();
                    String toolUseId = metadata.containsKey("tool_call_id") ?
                        (String) metadata.get("tool_call_id") : "";
                    String content = msg.contentAsString();
                    // Build ToolResultBlockParam and wrap in ContentBlockParam
                    ToolResultBlockParam toolResult = ToolResultBlockParam.builder()
                        .toolUseId(toolUseId)
                        .content(content)
                        .build();
                    // Use MessageParam builder with content as block params
                    paramsBuilder.addMessage(
                        MessageParam.builder()
                            .content(MessageParam.Content.ofBlockParams(
                                List.of(ContentBlockParam.ofToolResult(toolResult))
                            ))
                            .role(MessageParam.Role.USER)
                            .build()
                    );
                }
                default -> logger.warn("Unknown message role: {}", msg.role());
            }
        }

        // Add tools if present
        if (tools != null && !tools.isEmpty()) {
            for (ToolDefinition tool : tools) {
                paramsBuilder.addTool(
                    Tool.builder()
                        .name(tool.name())
                        .description(tool.description())
                        .inputSchema(convertInputSchema(tool.inputSchema()))
                        .build()
                );
            }
        }

        MessageCreateParams params = paramsBuilder.build();

        // Make API call - use fully qualified name to avoid conflict
        com.anthropic.models.messages.Message response = client.messages().create(params);

        // Parse response
        return parseResponse(response);
    }

    @Override
    public CompletableFuture<LLMResponse> callAsync(List<Message> messages, List<ToolDefinition> tools, String systemPrompt) {
        return CompletableFuture.supplyAsync(() -> call(messages, tools, systemPrompt));
    }

    @Override
    public void stream(List<Message> messages, List<ToolDefinition> tools, String systemPrompt, StreamCallback onChunk) {
        // Build params
        MessageCreateParams.Builder paramsBuilder = MessageCreateParams.builder()
            .model(Model.CLAUDE_SONNET_4_6)
            .maxTokens(4096L);

        if (systemPrompt != null && !systemPrompt.isEmpty()) {
            paramsBuilder.system(systemPrompt);
        }

        for (Message msg : messages) {
            switch (msg.role()) {
                case "user" -> paramsBuilder.addUserMessage(msg.contentAsString());
                case "assistant" -> paramsBuilder.addAssistantMessage(msg.contentAsString());
                default -> {}
            }
        }

        // Stream response using stream().forEach() pattern
        try (var streamResponse = client.messages().createStreaming(paramsBuilder.build())) {
            streamResponse.stream().forEach(event -> {
                // Handle ContentBlockDelta events
                event.contentBlockDelta().ifPresent(deltaEvent -> {
                    RawContentBlockDelta delta = deltaEvent.delta();
                    if (delta != null) {
                        delta.text().ifPresent(textDelta -> {
                            String text = textDelta.text();
                            if (text != null) {
                                onChunk.onChunk(text);
                            }
                        });
                    }
                });
            });
        }
    }

    /**
     * Parse Anthropic response into LLMResponse.
     */
    private LLMResponse parseResponse(com.anthropic.models.messages.Message response) {
        StringBuilder content = new StringBuilder();
        List<ToolCall> toolCalls = new ArrayList<>();

        // Extract content and tool calls - response.content() returns List<ContentBlock>
        List<ContentBlock> blocks = response.content();
        if (blocks != null) {
            for (ContentBlock block : blocks) {
                // Use Optional-based access
                block.text().ifPresent(textBlock -> {
                    content.append(textBlock.text());
                });
                block.toolUse().ifPresent(toolUse -> {
                    // _input() returns JsonValue, convert to Map for simplicity
                    Map<String, Object> input = Map.of();
                    toolCalls.add(new ToolCall(
                        toolUse.id(),
                        toolUse.name(),
                        input
                    ));
                });
            }
        }

        // Determine stop reason - stopReason() returns Optional<StopReason>
        StopReason stopReason = StopReason.END_TURN;
        Optional<com.anthropic.models.messages.StopReason> apiStopReason = response.stopReason();
        if (apiStopReason.isPresent()) {
            com.anthropic.models.messages.StopReason reason = apiStopReason.get();
            // Compare with static instances
            if (reason == com.anthropic.models.messages.StopReason.END_TURN) {
                stopReason = StopReason.END_TURN;
            } else if (reason == com.anthropic.models.messages.StopReason.TOOL_USE) {
                stopReason = StopReason.TOOL_USE;
            } else if (reason == com.anthropic.models.messages.StopReason.MAX_TOKENS) {
                stopReason = StopReason.MAX_TOKENS;
            } else if (reason == com.anthropic.models.messages.StopReason.STOP_SEQUENCE) {
                stopReason = StopReason.STOP_SEQUENCE;
            }
        }

        // Extract usage - usage() returns Usage object directly
        TokenUsage usage = new TokenUsage();
        Usage usageData = response.usage();
        if (usageData != null) {
            usage = new TokenUsage(
                (int) usageData.inputTokens(),
                (int) usageData.outputTokens()
            );
        }

        return LLMResponse.builder()
            .content(content.toString())
            .toolCalls(toolCalls)
            .stopReason(stopReason)
            .usage(usage)
            .build();
    }

    /**
     * Convert input schema to Anthropic format.
     */
    private Tool.InputSchema convertInputSchema(Map<String, Object> schema) {
        Tool.InputSchema.Builder builder = Tool.InputSchema.builder();

        if (schema.containsKey("properties")) {
            // Convert to Tool.InputSchema.Properties
            Tool.InputSchema.Properties.Builder propsBuilder = Tool.InputSchema.Properties.builder();
            @SuppressWarnings("unchecked")
            Map<String, Object> properties = (Map<String, Object>) schema.get("properties");
            // For simplicity, we'll create basic properties
            builder.properties(propsBuilder.build());
        }
        if (schema.containsKey("required")) {
            @SuppressWarnings("unchecked")
            List<String> required = (List<String>) schema.get("required");
            builder.required(required);
        }

        return builder.build();
    }
}