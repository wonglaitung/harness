package com.harness.core;

import java.util.*;

/**
 * Model presets for automatic context window configuration.
 *
 * Provides predefined configurations for common LLM models to simplify setup.
 *
 * Example:
 * <pre>
 * ModelPreset preset = ModelPresets.get("claude-sonnet-4-6");
 * System.out.println("Context window: " + preset.contextWindow());
 * System.out.println("Provider: " + preset.provider());
 * </pre>
 */
public class ModelPresets {

    /**
     * Model preset configuration.
     */
    public static class ModelPreset {
        private final String name;
        private final int contextWindow;
        private final int defaultOutputTokens;
        private final String provider;

        public ModelPreset(String name, int contextWindow, int defaultOutputTokens, String provider) {
            this.name = name;
            this.contextWindow = contextWindow;
            this.defaultOutputTokens = defaultOutputTokens;
            this.provider = provider;
        }

        public String name() { return name; }
        public int contextWindow() { return contextWindow; }
        public int defaultOutputTokens() { return defaultOutputTokens; }
        public String provider() { return provider; }
    }

    // Context level shortcuts
    public static final Map<String, Integer> CONTEXT_LEVELS = Map.of(
        "32k", 32768,
        "64k", 65536,
        "128k", 131072,
        "200k", 204800
    );

    // Default preset for unknown models
    public static final ModelPreset DEFAULT_PRESET = new ModelPreset(
        "default",
        65536,  // 64K as reasonable default
        8192,   // 8K output, leaving ~56K for input
        "auto"
    );

    // Predefined model configurations
    public static final Map<String, ModelPreset> MODEL_PRESETS = Map.ofEntries(
        // Anthropic Claude
        Map.entry("claude-opus-4-6", new ModelPreset("claude-opus-4-6", 200000, 16384, "anthropic")),
        Map.entry("claude-opus-4", new ModelPreset("claude-opus-4", 200000, 16384, "anthropic")),
        Map.entry("claude-sonnet-4-6", new ModelPreset("claude-sonnet-4-6", 200000, 16384, "anthropic")),
        Map.entry("claude-sonnet-4", new ModelPreset("claude-sonnet-4", 200000, 16384, "anthropic")),
        Map.entry("claude-haiku-4-5", new ModelPreset("claude-haiku-4-5", 200000, 8192, "anthropic")),
        Map.entry("claude-haiku-4", new ModelPreset("claude-haiku-4", 200000, 8192, "anthropic")),
        Map.entry("claude-3-opus", new ModelPreset("claude-3-opus", 200000, 4096, "anthropic")),
        Map.entry("claude-3-sonnet", new ModelPreset("claude-3-sonnet", 200000, 4096, "anthropic")),
        Map.entry("claude-3-haiku", new ModelPreset("claude-3-haiku", 200000, 4096, "anthropic")),
        Map.entry("claude-3-5-sonnet", new ModelPreset("claude-3-5-sonnet", 200000, 8192, "anthropic")),
        Map.entry("claude-3-5-haiku", new ModelPreset("claude-3-5-haiku", 200000, 8192, "anthropic")),

        // OpenAI GPT
        Map.entry("gpt-4o", new ModelPreset("gpt-4o", 128000, 16384, "openai")),
        Map.entry("gpt-4o-mini", new ModelPreset("gpt-4o-mini", 128000, 16384, "openai")),
        Map.entry("gpt-4-turbo", new ModelPreset("gpt-4-turbo", 128000, 4096, "openai")),
        Map.entry("gpt-4", new ModelPreset("gpt-4", 8192, 4096, "openai")),
        Map.entry("gpt-4-32k", new ModelPreset("gpt-4-32k", 32768, 4096, "openai")),
        Map.entry("gpt-3.5-turbo", new ModelPreset("gpt-3.5-turbo", 16385, 4096, "openai")),
        Map.entry("gpt-3.5-turbo-16k", new ModelPreset("gpt-3.5-turbo-16k", 16385, 4096, "openai")),
        Map.entry("o1", new ModelPreset("o1", 200000, 100000, "openai")),
        Map.entry("o1-mini", new ModelPreset("o1-mini", 128000, 65536, "openai")),
        Map.entry("o1-preview", new ModelPreset("o1-preview", 128000, 32768, "openai")),

        // GLM (Zhipu AI)
        Map.entry("glm-4", new ModelPreset("glm-4", 128000, 4096, "openai")),
        Map.entry("glm-4-plus", new ModelPreset("glm-4-plus", 128000, 4096, "openai")),
        Map.entry("glm-4-air", new ModelPreset("glm-4-air", 128000, 4096, "openai")),
        Map.entry("glm-4-flash", new ModelPreset("glm-4-flash", 128000, 4096, "openai")),
        Map.entry("glm-5", new ModelPreset("glm-5", 65536, 4096, "openai")),

        // Qwen (Alibaba)
        Map.entry("qwen-turbo", new ModelPreset("qwen-turbo", 128000, 6144, "openai")),
        Map.entry("qwen-plus", new ModelPreset("qwen-plus", 128000, 6144, "openai")),
        Map.entry("qwen-max", new ModelPreset("qwen-max", 32768, 6144, "openai")),
        Map.entry("qwen-72b", new ModelPreset("qwen-72b", 32768, 4096, "openai")),
        Map.entry("qwen2.5-72b", new ModelPreset("qwen2.5-72b", 131072, 8192, "openai")),

        // DeepSeek
        Map.entry("deepseek-chat", new ModelPreset("deepseek-chat", 64000, 4096, "openai")),
        Map.entry("deepseek-coder", new ModelPreset("deepseek-coder", 64000, 4096, "openai")),

        // Yi (01.AI)
        Map.entry("yi-large", new ModelPreset("yi-large", 32768, 4096, "openai")),
        Map.entry("yi-medium", new ModelPreset("yi-medium", 16384, 4096, "openai")),

        // LLaMA variants
        Map.entry("llama-3-70b", new ModelPreset("llama-3-70b", 8192, 4096, "openai")),
        Map.entry("llama-3-8b", new ModelPreset("llama-3-8b", 8192, 4096, "openai")),
        Map.entry("llama-3.1-70b", new ModelPreset("llama-3.1-70b", 131072, 4096, "openai")),
        Map.entry("llama-3.1-8b", new ModelPreset("llama-3.1-8b", 131072, 4096, "openai")),

        // Mistral
        Map.entry("mistral-large", new ModelPreset("mistral-large", 128000, 4096, "openai")),
        Map.entry("mistral-medium", new ModelPreset("mistral-medium", 32768, 4096, "openai")),
        Map.entry("mistral-small", new ModelPreset("mistral-small", 32768, 4096, "openai")),
        Map.entry("mixtral-8x7b", new ModelPreset("mixtral-8x7b", 32768, 4096, "openai")),
        Map.entry("mixtral-8x22b", new ModelPreset("mixtral-8x22b", 65536, 4096, "openai"))
    );

    /**
     * Get preset configuration for a model.
     *
     * @param model Model name
     * @return ModelPreset configuration, or default if unknown
     */
    public static ModelPreset get(String model) {
        if (model == null || model.isEmpty()) {
            return DEFAULT_PRESET;
        }

        // Normalize model name
        String normalized = model.toLowerCase().trim();

        // Direct lookup
        if (MODEL_PRESETS.containsKey(normalized)) {
            return MODEL_PRESETS.get(normalized);
        }

        // Try partial matching
        for (Map.Entry<String, ModelPreset> entry : MODEL_PRESETS.entrySet()) {
            if (normalized.contains(entry.getKey()) || entry.getKey().contains(normalized)) {
                return entry.getValue();
            }
        }

        return DEFAULT_PRESET;
    }

    /**
     * Parse context window specification to actual token count.
     *
     * @param contextWindow Can be int, String level ("64k"), or "auto"
     * @param model Model name (required if contextWindow is "auto")
     * @return Context window size in tokens
     */
    public static int parseContextWindow(Object contextWindow, String model) {
        if (contextWindow instanceof Integer) {
            return (Integer) contextWindow;
        }

        if (contextWindow instanceof String) {
            String str = ((String) contextWindow).toLowerCase().trim();

            // Check for level shortcuts
            if (CONTEXT_LEVELS.containsKey(str)) {
                return CONTEXT_LEVELS.get(str);
            }

            // Check for "auto"
            if ("auto".equals(str)) {
                return get(model).contextWindow();
            }

            // Try to parse as integer
            try {
                return Integer.parseInt(str);
            } catch (NumberFormatException e) {
                // Fall through
            }
        }

        return DEFAULT_PRESET.contextWindow();
    }

    /**
     * Get default output tokens for a model.
     */
    public static int getDefaultOutputTokens(String model) {
        return get(model).defaultOutputTokens();
    }

    /**
     * Get provider for a model.
     */
    public static String getProvider(String model) {
        return get(model).provider();
    }
}
