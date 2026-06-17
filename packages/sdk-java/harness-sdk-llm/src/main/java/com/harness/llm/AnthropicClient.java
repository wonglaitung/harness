package com.harness.llm;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.anthropic.client.AnthropicClient;
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

    private final AnthropicClient client;
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

        // Build request
        MessageCreateParams.Builder paramsBuilder = MessageCreateParams.builder()
            .model(Model.CLAUDE_SONNET_4_6) // Default model
            .maxTokens(4096);

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
                    // Handle tool result
                    Map<String, Object> metadata = msg.metadata();
                    String toolUseId = metadata.containsKey("tool_call_id") ?
                        (String) metadata.get("tool_call_id") : "";
                    String content = msg.contentAsString();
                    paramsBuilder.addToolResultMessage(toolUseId, content);
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

        // Make API call
        Message response = client.messages().create(params);

        // Parse response
        return parseResponse(response);
    }

    @Override
    public CompletableFuture<LLMResponse> callAsync(List<Message> messages, List<ToolDefinition> tools, String systemPrompt) {
        return CompletableFuture.supplyAsync(() -> call(messages, tools, systemPrompt));
    }

    @Override
    public void stream(List<Message> messages, List<ToolDefinition> tools, String systemPrompt, StreamCallback onChunk) {
        // Build params similar to call()
        MessageCreateParams.Builder paramsBuilder = MessageCreateParams.builder()
            .model(Model.CLAUDE_SONNET_4_6)
            .maxTokens(4096);

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

        // Stream response
        client.messages().createStreaming(paramsBuilder.build())
            .subscribe(event -> {
                if (event.contentBlockDelta() != null) {
                    ContentBlockDelta delta = event.contentBlockDelta();
                    if (delta.delta() != null && delta.delta().asTextDelta() != null) {
                        String text = delta.delta().asTextDelta().text();
                        if (text != null) {
                            onChunk.onChunk(text);
                        }
                    }
                }
            });
    }

    /**
     * Parse Anthropic response into LLMResponse.
     */
    private LLMResponse parseResponse(Message response) {
        String content = "";
        List<ToolCall> toolCalls = new ArrayList<>();

        // Extract content and tool calls
        for (ContentBlock block : response.content()) {
            if (block.isText()) {
                content += block.asText().text();
            } else if (block.isToolUse()) {
                ToolUseBlock toolUse = block.asToolUse();
                toolCalls.add(new ToolCall(
                    toolUse.id(),
                    toolUse.name(),
                    toolUse.input() != null ? toolUse.input() : Map.of()
                ));
            }
        }

        // Determine stop reason
        StopReason stopReason = StopReason.END_TURN;
        if (response.stopReason() != null) {
            switch (response.stopReason()) {
                case MessageStopReason.END_TURN -> stopReason = StopReason.END_TURN;
                case MessageStopReason.TOOL_USE -> stopReason = StopReason.TOOL_USE;
                case MessageStopReason.MAX_TOKENS -> stopReason = StopReason.MAX_TOKENS;
                default -> stopReason = StopReason.END_TURN;
            }
        }

        // Extract usage
        TokenUsage usage = new TokenUsage(
            response.usage() != null ? response.usage().inputTokens() : 0,
            response.usage() != null ? response.usage().outputTokens() : 0
        );

        return LLMResponse.builder()
            .content(content)
            .toolCalls(toolCalls)
            .stopReason(stopReason)
            .usage(usage)
            .build();
    }

    /**
     * Convert input schema to Anthropic format.
     */
    private ToolInputSchema convertInputSchema(Map<String, Object> schema) {
        // Anthropic expects a specific schema format
        return ToolInputSchema.builder()
            .type("object")
            .properties(schema.getOrDefault("properties", Map.of()))
            .required((List<String>) schema.getOrDefault("required", List.of()))
            .build();
    }
}