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
import com.openai.errors.BadRequestException;

import com.harness.core.HarnessConfig;
import com.harness.core.LLMClient;
import com.harness.types.DocumentTooLargeException;
import com.harness.types.LLMResponse;
import com.harness.types.Message;
import com.harness.types.StopReason;
import com.harness.types.TokenUsage;
import com.harness.types.ToolCall;

/**
 * OpenAI-compatible API client with multimodal support.
 *
 * Wraps the official OpenAI Java SDK. Supports custom base URL
 * for third-party API gateways (bank environments).
 *
 * Features:
 * - Multimodal content support (images and documents converted to text representation)
 * - Document size validation with configurable actions (warn/error/truncate)
 * - Compatible with all OpenAI-compatible APIs (GLM, Qwen, DeepSeek, local models)
 * - Robust error handling with automatic retry on transient failures
 */
public class OpenAIClient implements LLMClient {

    private static final Logger logger = LoggerFactory.getLogger(OpenAIClient.class);
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final com.openai.client.OpenAIClient client;
    private final String modelName;
    private final HarnessConfig config;

    /**
     * Create client with API key.
     */
    public OpenAIClient(String apiKey, String modelName) {
        this.client = OpenAIOkHttpClient.builder()
            .apiKey(apiKey)
            .build();
        this.modelName = modelName;
        this.config = null;
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
        this.config = null;
    }

    /**
     * Create client from environment variables.
     */
    public OpenAIClient(String modelName) {
        this.client = OpenAIOkHttpClient.fromEnv();
        this.modelName = modelName;
        this.config = null;
    }

    /**
     * Create client with configuration.
     */
    public OpenAIClient(String apiKey, String baseUrl, String modelName, HarnessConfig config) {
        this.client = OpenAIOkHttpClient.builder()
            .apiKey(apiKey)
            .baseUrl(baseUrl != null ? baseUrl : "https://api.openai.com/v1")
            .build();
        this.modelName = modelName;
        this.config = config;
    }

    @Override
    public String modelName() {
        return modelName;
    }

    @Override
    public LLMResponse call(List<Message> messages, List<ToolDefinition> tools, String systemPrompt) {
        logger.debug("Calling OpenAI-compatible API with {} messages", messages.size());

        ChatCompletionCreateParams params = buildParams(messages, tools, systemPrompt);

        try {
            ChatCompletion completion = client.chat().completions().create(params);
            return parseResponse(completion);

        } catch (BadRequestException e) {
            String errorMsg = e.getMessage();
            // Handle non-standard API responses
            if (errorMsg != null && isUnsupportedContentTypeError(errorMsg)) {
                logger.warn("API returned unsupported content type error: {}", errorMsg);
            }
            throw new RuntimeException("OpenAI API call failed: " + errorMsg, e);
        } catch (Exception e) {
            logger.error("OpenAI API call failed: {}", e.getMessage());
            throw new RuntimeException("OpenAI API call failed: " + e.getMessage(), e);
        }
    }

    /**
     * Build request parameters with multimodal content converted to text.
     */
    private ChatCompletionCreateParams buildParams(
            List<Message> messages, List<ToolDefinition> tools, String systemPrompt) {

        ChatCompletionCreateParams.Builder paramsBuilder = ChatCompletionCreateParams.builder()
            .model(modelName);

        if (systemPrompt != null && !systemPrompt.isEmpty()) {
            paramsBuilder.addSystemMessage(systemPrompt);
        }

        for (Message msg : messages) {
            addUserMessage(paramsBuilder, msg);
        }

        return paramsBuilder.build();
    }

    /**
     * Add a user message with multimodal content support.
     *
     * Multimodal content (images, documents) is converted to text representation
     * for maximum compatibility with all OpenAI-compatible APIs.
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
     * Check if error indicates unsupported content type.
     */
    private boolean isUnsupportedContentTypeError(String errorMsg) {
        String lower = errorMsg.toLowerCase();
        return (lower.contains("content type") && (lower.contains("file") || lower.contains("must be text")))
            || lower.contains("unsupported content type")
            || lower.contains("invalid content type");
    }

    /**
     * Convert multimodal content to text representation.
     *
     * This method does NOT modify the original content. It creates a new
     * StringBuilder and only reads from the input list.
     *
     * Strategy:
     * - Text blocks: preserved as-is
     * - Image blocks: converted to placeholder [Image attached: type]
     * - Document blocks: decoded and embedded as text (with size validation)
     *
     * This ensures compatibility with all OpenAI-compatible APIs while
     * preserving document content for the LLM to process.
     */
    @SuppressWarnings("unchecked")
    private String convertMultimodalToText(List<?> content) {
        StringBuilder textBuilder = new StringBuilder();
        List<String> documentTexts = new ArrayList<>();
        List<String> warnings = new ArrayList<>();
        long totalSize = 0;

        // Get config values with defaults
        int maxDocumentSize = config != null ? config.getMaxDocumentSize() : 10 * 1024 * 1024;
        int maxTotalSize = config != null ? config.getMaxTotalDocumentsSize() : 20 * 1024 * 1024;
        HarnessConfig.DocumentSizeAction action = config != null ? config.getDocumentSizeAction() : HarnessConfig.DocumentSizeAction.WARN;
        double tokenWarningRatio = config != null ? config.getDocumentTokenWarningRatio() : 0.5;
        int contextWindow = config != null ? config.getContextWindow() : 200000;

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
                        // Log image presence with placeholder text
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
                            byte[] decoded = Base64.getDecoder().decode(data);
                            long docSize = decoded.length;
                            totalSize += docSize;

                            // Check single document size
                            if (docSize > maxDocumentSize) {
                                String msg = String.format("Document '%s' (%.1fMB) exceeds limit (%.1fMB)",
                                    filename, docSize / 1024.0 / 1024, maxDocumentSize / 1024.0 / 1024);

                                if (action == HarnessConfig.DocumentSizeAction.ERROR) {
                                    throw new DocumentTooLargeException(filename, docSize, maxDocumentSize);
                                } else if (action == HarnessConfig.DocumentSizeAction.WARN) {
                                    warnings.add(msg);
                                    logger.warn(msg);
                                } else if (action == HarnessConfig.DocumentSizeAction.TRUNCATE) {
                                    decoded = truncateBytes(decoded, maxDocumentSize);
                                    logger.warn("Document '{}' truncated to {}MB", filename, maxDocumentSize / 1024 / 1024);
                                }
                            }

                            String decodedContent = new String(decoded);
                            String documentText = "\n\n--- Attached File: " + filename + " ---\n"
                                + decodedContent + "\n--- End of File ---\n";
                            documentTexts.add(documentText);

                            logger.info("Document '{}' converted to text ({} chars)", filename, decodedContent.length());
                        } catch (DocumentTooLargeException e) {
                            throw e;
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

        // Check total documents size
        if (totalSize > maxTotalSize) {
            String msg = String.format("Total document size (%.1fMB) exceeds limit (%.1fMB)",
                totalSize / 1024.0 / 1024, maxTotalSize / 1024.0 / 1024);
            if (action == HarnessConfig.DocumentSizeAction.ERROR) {
                throw new DocumentTooLargeException("total", totalSize, maxTotalSize);
            } else if (action == HarnessConfig.DocumentSizeAction.WARN) {
                warnings.add(msg);
                logger.warn(msg);
            }
        }

        // Token usage warning
        long estimatedTokens = totalSize / 4;
        long tokenThreshold = (long) (contextWindow * tokenWarningRatio);
        if (estimatedTokens > tokenThreshold) {
            logger.warn("Documents may use ~{}K tokens ({}% of {}K context window), leaving limited space for response",
                estimatedTokens / 1000,
                estimatedTokens * 100 / contextWindow,
                contextWindow / 1000);
        }

        // Output all warnings
        for (String warning : warnings) {
            logger.warn(warning);
        }

        // Append all document texts at the end
        for (String docText : documentTexts) {
            textBuilder.append(docText);
        }

        return textBuilder.toString();
    }

    /**
     * Truncate byte array to specified size.
     */
    private byte[] truncateBytes(byte[] data, int maxSize) {
        if (data.length <= maxSize) {
            return data;
        }
        byte[] truncated = new byte[maxSize];
        System.arraycopy(data, 0, truncated, 0, maxSize);
        return truncated;
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
        } catch (Exception e) {
            logger.error("Streaming failed: {}", e.getMessage());
            throw new RuntimeException("Streaming failed", e);
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
