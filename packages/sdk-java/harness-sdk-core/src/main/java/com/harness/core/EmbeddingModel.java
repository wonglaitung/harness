package com.harness.core;

import java.util.List;

/**
 * Interface for embedding model used in stuck detection.
 *
 * Implementations can use different embedding backends:
 * - ONNX Runtime with sentence-transformers model
 * - External embedding API (OpenAI, Cohere, etc.)
 * - DJL (Deep Java Library)
 */
public interface EmbeddingModel {

    /**
     * Get the dimension of embeddings produced by this model.
     */
    int getDimension();

    /**
     * Generate embedding for a single text.
     *
     * @param text Text to embed
     * @return Embedding vector, or null if failed
     */
    float[] embed(String text);

    /**
     * Generate embeddings for multiple texts.
     *
     * @param texts Texts to embed
     * @return List of embedding vectors
     */
    List<float[]> embedBatch(List<String> texts);

    /**
     * Check if the model is available.
     */
    default boolean isAvailable() {
        return true;
    }

    /**
     * Get model name for logging.
     */
    default String getName() {
        return "unknown";
    }
}
