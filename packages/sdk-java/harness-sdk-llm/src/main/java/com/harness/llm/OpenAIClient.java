package com.harness.llm;

import java.util.ArrayList;
import java.util.Base64;
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
 *
 * Features:
 * - Multimodal content support (images and documents converted to text)
 * - Compatible with all OpenAI-compatible APIs
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

        // Add messages with multimodal support
        for (Message msg : messages) {
            addUserMessage(paramsBuilder, msg);
        }

        // Note: Tools are added via addTool(Class) for typed tools
        // For dynamic tools, we skip them in this simplified implementation

        ChatCompletionCreateParams params = paramsBuilder.build();

        // Make API call
        try {
            ChatCompletion completion = client.chat().completions().create(params);
            return parseResponse(completion);

        } catch (Exception e) {
            logger.error("OpenAI API call failed: {}", e.getMessage());
            throw new RuntimeException("OpenAI API call failed: " + e.getMessage(), e);
        }
    }

    /**
     * Add a user message with multimodal content support.
     *
     * Note: OpenAI Java SDK 4.x multimodal API differs from documented examples.
     * We convert multimodal content to text representation for compatibility.
     */
    @SuppressWarnings("unchecked")
    private void addUserMessage(ChatCompletionCreateParams.Builder paramsBuilder, Message msg) {
        switch (msg.role()) {
            case "user" -> {
                Object content = msg.content();
                if (content instanceof String text) {
                    paramsBuilder.addUserMessage(text);
                } else if (content instanceof List<?> contentList) {
                    // Multimodal content - convert to text representation
                    String textContent = convertMultimodalToText(contentList);
                    paramsBuilder.addUserMessage(textContent);
                } else {
                    paramsBuilder.addUserMessage(msg.contentAsString());
                }
            }
            case "assistant" -> paramsBuilder.addAssistantMessage(msg.contentAsString());
            case "tool" -> {
                Map<String, Object> metadata = msg.metadata();
                String toolCallId = metadata.containsKey("tool_call_id") ?
                    (String) metadata.get("tool_call_id") : "";
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

    /**
     * Convert multimodal content to text representation.
     *
     * This approach ensures compatibility with all OpenAI-compatible APIs
     * and doesn't depend on SDK-specific multimodal APIs that may change.
     */
    @SuppressWarnings("unchecked")
    private String convertMultimodalToText(List<?> content) {
        StringBuilder textBuilder = new StringBuilder();

        for (Object item : content) {
            if (item instanceof Map<?, ?> block) {
                String blockType = (String) block.get("type");

                switch (blockType) {
                    case "text" -> {
                        String text = (String) block.get("text");
                        if (text != null && !text.isEmpty()) {
                            textBuilder.append(text);
                        }
                    }
                    case "image" -> {
                        // Log image presence - actual image data would need proper multimodal API
                        Map<String, Object> source = (Map<String, Object>) block.get("source");
                        if (source != null) {
                            String mediaType = (String) source.getOrDefault("media_type", "image/png");
                            logger.debug("Image attachment detected (type: {})", mediaType);
                            textBuilder.append("\n[Image attached: ").append(mediaType).append("]\n");
                        }
                    }
                    case "document" -> {
                        // Decode and include document content
                        Map<String, Object> source = (Map<String, Object>) block.get("source");
                        String data = source != null ? (String) source.get("data") : "";
                        Object filenameObj = block.get("filename");
                        String filename = filenameObj != null ? filenameObj.toString() : "document";

                        try {
                            String decodedContent = new String(Base64.getDecoder().decode(data));
                            textBuilder.append("\n\n--- Attached File: ").append(filename).append(" ---\n");
                            textBuilder.append(decodedContent);
                            textBuilder.append("\n--- End of File ---\n");

                            logger.info("Document '{}' converted to text ({} chars)", filename, decodedContent.length());
                        } catch (Exception e) {
                            logger.warn("Failed to decode document '{}': {}", filename, e.getMessage());
                            textBuilder.append("\n[Document attachment: ").append(filename).append(" - could not decode]\n");
                        }
                    }
                    default -> {
                        logger.debug("Unknown content block type: {}", blockType);
                    }
                }
            }
        }

        return textBuilder.toString();
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
            if (finishReason == ChatCompletion.Choice.FinishReason.STOP) {
                stopReason = StopReason.END_TURN;
            } else if (finishReason == ChatCompletion.Choice.FinishReason.TOOL_CALLS) {
                stopReason = StopReason.TOOL_USE;
            } else if (finishReason == ChatCompletion.Choice.FinishReason.LENGTH) {
                stopReason = StopReason.MAX_TOKENS;
            }
        }

        // Extract usage
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
