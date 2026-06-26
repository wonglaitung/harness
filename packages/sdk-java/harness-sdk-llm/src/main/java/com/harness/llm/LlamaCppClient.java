package com.harness.llm;

import java.nio.file.Path;
import java.util.*;
import java.util.concurrent.*;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.core.LLMClient;
import com.harness.core.ModelPresets;
import com.harness.types.LLMResponse;
import com.harness.types.Message;
import com.harness.types.StopReason;
import com.harness.types.TokenUsage;

/**
 * Embedded Llama client for GGUF models.
 *
 * Provides CPU-based inference for GGUF models (e.g., Qwen2.5-1.5B)
 * for use as a routing classifier.
 *
 * Note: This implementation requires llama.cpp JNI bindings.
 * Install llama.cpp with Java bindings before using.
 *
 * Example:
 * <pre>
 * LlamaCppClient client = LlamaCppClient.builder()
 *     .modelPath("models/qwen2.5-1.5b-instruct-q4_k_m.gguf")
 *     .contextWindow("auto")  // Infers from filename
 *     .build();
 *
 * LLMResponse response = client.call(messages, null, null);
 * </pre>
 */
public class LlamaCppClient implements LLMClient {

    private static final Logger logger = LoggerFactory.getLogger(LlamaCppClient.class);

    // GGUF filename patterns to strip when extracting model name
    private static final List<String> QUANTIZATION_SUFFIXES = List.of(
        "-q4_k_m", "-q4_k_s", "-q4_0", "-q5_k_m", "-q5_k_s", "-q5_0",
        "-q6_k", "-q8_0", "-f16", "-bf16"
    );
    private static final List<String> OTHER_SUFFIXES = List.of("-instruct", "-chat");

    private final String modelPath;
    private final int contextWindow;
    private final int nGpuLayers;
    private final int maxTokens;
    private final double temperature;
    private final ExecutorService executor;

    // Lazy-loaded model (would be llama.cpp model object in real implementation)
    private volatile boolean loaded = false;

    private LlamaCppClient(Builder builder) {
        this.modelPath = builder.modelPath;
        this.nGpuLayers = builder.nGpuLayers;
        this.maxTokens = builder.maxTokens;
        this.temperature = builder.temperature;

        // Parse context_window using model_presets pattern
        String modelName = extractModelName(modelPath);
        int parsedCtx = ModelPresets.parseContextWindow(builder.contextWindow, modelName);

        // For router models, use smaller default than DEFAULT_PRESET (64k)
        // Routing tasks typically need ~500-800 tokens, 2048 is sufficient
        if (parsedCtx == ModelPresets.DEFAULT_PRESET.contextWindow()) {
            this.contextWindow = 2048;
            logger.debug("Unknown model '{}', using default ctx=2048 for routing", modelName);
        } else {
            this.contextWindow = parsedCtx;
            logger.debug("Model '{}' contextWindow={}", modelName, this.contextWindow);
        }

        // Single-threaded executor for llama.cpp calls
        this.executor = Executors.newSingleThreadExecutor(r -> {
            Thread t = new Thread(r, "llama-cpp");
            t.setDaemon(true);
            return t;
        });
    }

    /**
     * Extract model name from GGUF file path.
     *
     * Example: "models/qwen3.5-0.8b-instruct-q4_k_m.gguf" → "qwen3.5-0.8b"
     */
    private String extractModelName(String modelPath) {
        String filename = Path.of(modelPath).getFileName().toString();

        // Remove .gguf extension
        if (filename.endsWith(".gguf")) {
            filename = filename.substring(0, filename.length() - 5);
        }

        // Strip quantization suffixes
        for (String suffix : QUANTIZATION_SUFFIXES) {
            filename = filename.replace(suffix, "");
        }

        // Strip other common suffixes
        for (String suffix : OTHER_SUFFIXES) {
            filename = filename.replace(suffix, "");
        }

        // Clean up any remaining artifacts
        filename = filename.replaceAll("[-_]+$", "");

        return filename;
    }

    /**
     * Load the GGUF model (lazy loading).
     */
    private synchronized void loadModel() {
        if (loaded) {
            return;
        }

        logger.info("Loading GGUF model: {} (n_ctx={})", modelPath, contextWindow);

        // In a real implementation, this would call llama.cpp JNI bindings:
        // this.model = new LlamaModel(modelPath, contextWindow, nGpuLayers);

        // For now, we'll log a warning that native bindings are not available
        logger.warn(
            "LlamaCppClient requires llama.cpp JNI bindings. " +
            "Model loading is simulated. Install llama.cpp with Java support for real inference."
        );

        loaded = true;
        logger.info("Model loaded successfully: {}", modelPath);
    }

    @Override
    public String modelName() {
        return modelPath;
    }

    @Override
    public LLMResponse call(List<Message> messages, List<ToolDefinition> tools, String systemPrompt) {
        // Lazy load on first call
        if (!loaded) {
            loadModel();
        }

        // In a real implementation, this would call llama.cpp JNI:
        // return model.createChatCompletion(messages, maxTokens, temperature);

        // Simulated response for now
        logger.warn("LlamaCppClient.call() is simulated - no native bindings available");

        return LLMResponse.builder()
            .content("[Simulated response - install llama.cpp JNI bindings for real inference]")
            .toolCalls(List.of())
            .stopReason(StopReason.END_TURN)
            .usage(new TokenUsage(10, 5))
            .build();
    }

    @Override
    public CompletableFuture<LLMResponse> callAsync(List<Message> messages, List<ToolDefinition> tools, String systemPrompt) {
        return CompletableFuture.supplyAsync(() -> call(messages, tools, systemPrompt), executor);
    }

    @Override
    public void stream(List<Message> messages, List<ToolDefinition> tools, String systemPrompt, StreamCallback onChunk) {
        LLMResponse response = call(messages, tools, systemPrompt);
        if (response.content() != null && onChunk != null) {
            onChunk.onChunk(response.content());
        }
    }

    /**
     * Close the client and release resources.
     */
    public void close() {
        executor.shutdown();
        try {
            if (!executor.awaitTermination(5, TimeUnit.SECONDS)) {
                executor.shutdownNow();
            }
        } catch (InterruptedException e) {
            executor.shutdownNow();
            Thread.currentThread().interrupt();
        }
    }

    // -------------------------------------------------------------------------
    // Builder
    // -------------------------------------------------------------------------

    public static Builder builder() {
        return new Builder();
    }

    public static class Builder {
        private String modelPath;
        private Object contextWindow = "auto";  // Can be int or "auto"
        private int nGpuLayers = 0;  // 0 = CPU only
        private int maxTokens = 10;
        private double temperature = 0.0;

        public Builder modelPath(String v) { this.modelPath = v; return this; }
        public Builder contextWindow(int v) { this.contextWindow = v; return this; }
        public Builder contextWindowAuto() { this.contextWindow = "auto"; return this; }
        public Builder nGpuLayers(int v) { this.nGpuLayers = v; return this; }
        public Builder maxTokens(int v) { this.maxTokens = v; return this; }
        public Builder temperature(double v) { this.temperature = v; return this; }

        public LlamaCppClient build() {
            if (modelPath == null || modelPath.isEmpty()) {
                throw new IllegalArgumentException("modelPath is required");
            }
            return new LlamaCppClient(this);
        }
    }
}
