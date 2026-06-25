package com.harness.memory;

/**
 * Result from a vector search.
 */
public record VectorSearchResult(
    String id,
    String content,
    double score,
    double retrievalStrength,
    java.util.Map<String, Object> metadata
) {

    public VectorSearchResult(String id, String content, double score) {
        this(id, content, score, 1.0, java.util.Map.of());
    }

    /**
     * Create with metadata.
     */
    public VectorSearchResult withMetadata(java.util.Map<String, Object> metadata) {
        return new VectorSearchResult(id, content, score, retrievalStrength, metadata);
    }

    /**
     * Create with retrieval strength.
     */
    public VectorSearchResult withRetrievalStrength(double strength) {
        return new VectorSearchResult(id, content, score, strength, metadata);
    }
}
