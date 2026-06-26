package com.harness.core;

/**
 * Model preset configuration.
 *
 * Contains provider-specific settings and limits for a specific model.
 */
public record ModelPreset(
    String provider,       // "anthropic", "openai", etc.
    int contextWindow,     // Maximum context window size
    int maxTokens,         // Default output token limit
    double inputPrice,     // Price per 1M input tokens (USD)
    double outputPrice     // Price per 1M output tokens (USD)
) {

    /**
     * Create a preset with default pricing.
     */
    public static ModelPreset of(String provider, int contextWindow, int maxTokens) {
        return new ModelPreset(provider, contextWindow, maxTokens, 0.0, 0.0);
    }

    /**
     * Create a preset with pricing.
     */
    public static ModelPreset of(String provider, int contextWindow, int maxTokens, double inputPrice, double outputPrice) {
        return new ModelPreset(provider, contextWindow, maxTokens, inputPrice, outputPrice);
    }
}
