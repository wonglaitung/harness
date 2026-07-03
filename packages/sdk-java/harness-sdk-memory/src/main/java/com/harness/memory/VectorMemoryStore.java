package com.harness.memory;

import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.core.EmbeddingModel;
import com.harness.core.OpenAIEmbeddingModel;
import com.harness.core.OnnxEmbeddingModel;

import java.nio.file.Path;

/**
 * Vector-based memory store for semantic search.
 *
 * Provides semantic search capabilities over:
 * - Conversation history
 * - Skill content
 * - Documents and notes
 * - Archived memory (Retrieved Memory)
 *
 * Supports Retrieval Strength weighting (Mem0-style decay):
 * - Time decay: older entries decay but never below min_strength
 * - Access bonus: frequently accessed entries get bonus
 *
 * <h2>Example with OpenAI</h2>
 * <pre>{@code
 * VectorMemoryStore store = new VectorMemoryStore(
 *     VectorMemoryConfig.builder()
 *         .embeddingModel("openai:text-embedding-3-small")
 *         .build(),
 *     new OpenAIEmbeddingModel("sk-...", "text-embedding-3-small")
 * );
 * store.add("doc1", "Python async patterns").join();
 *
 * List<VectorSearchResult> results = store.search("concurrency in Python", 5, true).join();
 * }</pre>
 *
 * <h2>Example with ONNX (local)</h2>
 * <pre>{@code
 * VectorMemoryStore store = new VectorMemoryStore(
 *     VectorMemoryConfig.builder()
 *         .embeddingModel("onnx:all-MiniLM-L6-v2")
 *         .embeddingDimension(384)
 *         .build(),
 *     new OnnxEmbeddingModel(Path.of("models/all-MiniLM-L6-v2.onnx"), 384)
 * );
 * }</pre>
 */
public class VectorMemoryStore {

    private static final Logger logger = LoggerFactory.getLogger(VectorMemoryStore.class);

    private final VectorMemoryConfig config;
    private final EmbeddingModel embeddingModel;
    private final SimpleVectorStore vectorStore;

    // Track archived entries for Retrieval Strength calculation
    private final Map<String, ArchivedMemoryEntry> entries = new HashMap<>();

    /**
     * Create store with default configuration (mock embedding).
     */
    public VectorMemoryStore() {
        this(VectorMemoryConfig.defaults());
    }

    /**
     * Create store with configuration (uses mock embedding by default).
     *
     * @param config Configuration
     */
    public VectorMemoryStore(VectorMemoryConfig config) {
        this(config, null);
    }

    /**
     * Create store with configuration and custom embedding model.
     *
     * @param config Configuration
     * @param embeddingModel Custom embedding model (null uses mock)
     */
    public VectorMemoryStore(VectorMemoryConfig config, EmbeddingModel embeddingModel) {
        this.config = config;
        this.embeddingModel = embeddingModel != null ? embeddingModel : createDefaultEmbeddingModel(config);
        this.vectorStore = new SimpleVectorStore();

        logger.info("VectorMemoryStore initialized: model={}, dimension={}",
            this.embeddingModel.getName(), this.embeddingModel.getDimension());
    }

    /**
     * Create default embedding model based on config.
     */
    private EmbeddingModel createDefaultEmbeddingModel(VectorMemoryConfig config) {
        String modelSpec = config.embeddingModel();

        if (modelSpec == null || modelSpec.equals("mock")) {
            logger.warn("Using mock embedding model - not suitable for production");
            return new MockEmbeddingModel(config.embeddingDimension());
        }

        // Parse model specification: "provider:model"
        String[] parts = modelSpec.split(":", 2);
        String provider = parts[0];
        String modelName = parts.length > 1 ? parts[1] : "text-embedding-3-small";

        try {
            switch (provider.toLowerCase()) {
                case "openai":
                    String apiKey = System.getenv("OPENAI_API_KEY");
                    if (apiKey == null || apiKey.isEmpty()) {
                        logger.warn("OPENAI_API_KEY not set, falling back to mock");
                        return new MockEmbeddingModel(config.embeddingDimension());
                    }
                    return new OpenAIEmbeddingModel(apiKey, modelName);

                case "onnx":
                    // modelName is path to ONNX file
                    Path modelPath = Path.of(modelName);
                    return new OnnxEmbeddingModel(modelPath, config.embeddingDimension());

                default:
                    logger.warn("Unknown embedding provider: {}, using mock", provider);
                    return new MockEmbeddingModel(config.embeddingDimension());
            }
        } catch (Exception e) {
            logger.error("Failed to create embedding model: {}, using mock", e.getMessage());
            return new MockEmbeddingModel(config.embeddingDimension());
        }
    }

    /**
     * Get the embedding model in use.
     */
    public EmbeddingModel getEmbeddingModel() {
        return embeddingModel;
    }

    /**
     * Add a single document to the store.
     */
    public CompletableFuture<Void> add(String id, String content) {
        return add(id, content, null);
    }

    /**
     * Add a single document to the store.
     */
    public CompletableFuture<Void> add(String id, String content, Map<String, Object> metadata) {
        return CompletableFuture.supplyAsync(() -> {
            float[] embedding = embeddingModel.embed(content);
            vectorStore.add(id, embedding, content, metadata);

            // Track entry for Retrieval Strength if it's archived memory
            if (metadata != null && "core_memory".equals(metadata.get("archived_from"))) {
                entries.put(id, new ArchivedMemoryEntry(
                    id, content,
                    (String) metadata.getOrDefault("category", "unknown"),
                    ((Number) metadata.getOrDefault("importance", 1.0)).doubleValue(),
                    LocalDateTime.now()
                ));
            }

            return null;
        });
    }

    /**
     * Add multiple documents to the store.
     */
    public CompletableFuture<Void> addBatch(List<String> ids, List<String> contents, List<Map<String, Object>> metadatas) {
        return CompletableFuture.supplyAsync(() -> {
            List<float[]> embeddings = embeddingModel.embedBatch(contents);
            for (int i = 0; i < ids.size(); i++) {
                String id = ids.get(i);
                String content = contents.get(i);
                Map<String, Object> metadata = metadatas != null && i < metadatas.size() ? metadatas.get(i) : null;
                float[] embedding = embeddings.get(i);

                vectorStore.add(id, embedding, content, metadata);
            }
            return null;
        });
    }

    /**
     * Search for similar documents.
     *
     * @param query Search query text
     * @param topK Maximum results to return
     * @param applyDecay If True, apply Retrieval Strength weighting
     * @return List of search results
     */
    public CompletableFuture<List<VectorSearchResult>> search(String query, int topK, boolean applyDecay) {
        return CompletableFuture.supplyAsync(() -> {
            float[] queryEmbedding = embeddingModel.embed(query);
            List<VectorSearchResult> rawResults = vectorStore.search(queryEmbedding, topK * 2);

            if (!applyDecay) {
                return rawResults.subList(0, Math.min(topK, rawResults.size()));
            }

            // Apply Retrieval Strength weighting
            List<ScoredResult> scoredResults = new ArrayList<>();
            for (VectorSearchResult result : rawResults) {
                ArchivedMemoryEntry entry = entries.get(result.id());

                double finalScore = result.score();
                double strength = 1.0;

                if (entry != null) {
                    strength = entry.calculateRetrievalStrength(
                        config.decayLambda(),
                        config.minRetrievalStrength()
                    );
                    finalScore = result.score() * strength;
                    entry.touch(); // Update access count
                }

                scoredResults.add(new ScoredResult(
                    new VectorSearchResult(
                        result.id(),
                        result.content(),
                        finalScore,
                        strength,
                        result.metadata()
                    ),
                    entry
                ));
            }

            // Sort by weighted score descending
            scoredResults.sort((a, b) -> Double.compare(b.result.score(), a.result.score()));

            // Return top K
            List<VectorSearchResult> results = new ArrayList<>();
            for (int i = 0; i < Math.min(topK, scoredResults.size()); i++) {
                results.add(scoredResults.get(i).result);
            }

            return results;
        });
    }

    /**
     * Delete documents by IDs.
     */
    public CompletableFuture<Void> delete(List<String> ids) {
        return CompletableFuture.supplyAsync(() -> {
            for (String id : ids) {
                vectorStore.delete(id);
                entries.remove(id);
            }
            return null;
        });
    }

    /**
     * Clear all documents.
     */
    public CompletableFuture<Void> clear() {
        return CompletableFuture.supplyAsync(() -> {
            vectorStore.clear();
            entries.clear();
            return null;
        });
    }

    /**
     * Add skill content to the store.
     */
    public CompletableFuture<Void> addSkill(String skillName, String content) {
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("type", "skill");
        metadata.put("skill_name", skillName);
        return add("skill_" + skillName, content, metadata);
    }

    /**
     * Search skills by semantic similarity.
     */
    public CompletableFuture<List<VectorSearchResult>> searchSkills(String query, int topK) {
        return search(query, topK, false).thenApply(results -> {
            List<VectorSearchResult> skillResults = new ArrayList<>();
            for (VectorSearchResult r : results) {
                if (r.metadata() != null && "skill".equals(r.metadata().get("type"))) {
                    skillResults.add(r);
                }
            }
            return skillResults;
        });
    }

    // -------------------------------------------------------------------------
    // Internal classes
    // -------------------------------------------------------------------------

    private static class ScoredResult {
        final VectorSearchResult result;
        final ArchivedMemoryEntry entry;

        ScoredResult(VectorSearchResult result, ArchivedMemoryEntry entry) {
            this.result = result;
            this.entry = entry;
        }
    }

    /**
     * Mock embedding model for testing.
     * Implements EmbeddingModel interface for compatibility.
     */
    private static class MockEmbeddingModel implements EmbeddingModel {
        private final int dimension;

        MockEmbeddingModel(int dimension) {
            this.dimension = dimension;
        }

        @Override
        public int getDimension() {
            return dimension;
        }

        @Override
        public float[] embed(String text) {
            // Generate deterministic embedding based on text content
            float[] embedding = new float[dimension];
            int hash = text != null ? text.hashCode() : 0;
            for (int i = 0; i < dimension; i++) {
                embedding[i] = ((hash >> (i % 32)) & 0xFF) / 255.0f - 0.5f;
            }
            return embedding;
        }

        @Override
        public List<float[]> embedBatch(List<String> texts) {
            List<float[]> results = new ArrayList<>();
            for (String text : texts) {
                results.add(embed(text));
            }
            return results;
        }

        @Override
        public String getName() {
            return "mock";
        }
    }

    /**
     * Simple in-memory vector store.
     */
    private static class SimpleVectorStore {
        private final Map<String, float[]> vectors = new HashMap<>();
        private final Map<String, String> documents = new HashMap<>();
        private final Map<String, Map<String, Object>> metadatas = new HashMap<>();

        void add(String id, float[] embedding, String document, Map<String, Object> metadata) {
            vectors.put(id, embedding);
            documents.put(id, document);
            if (metadata != null) {
                metadatas.put(id, metadata);
            }
        }

        List<VectorSearchResult> search(float[] queryEmbedding, int topK) {
            List<Map.Entry<String, Float>> scores = new ArrayList<>();

            for (Map.Entry<String, float[]> entry : vectors.entrySet()) {
                float similarity = cosineSimilarity(queryEmbedding, entry.getValue());
                scores.add(Map.entry(entry.getKey(), similarity));
            }

            // Sort by score descending
            scores.sort((a, b) -> Float.compare(b.getValue(), a.getValue()));

            // Return top K
            List<VectorSearchResult> results = new ArrayList<>();
            for (int i = 0; i < Math.min(topK, scores.size()); i++) {
                Map.Entry<String, Float> entry = scores.get(i);
                String id = entry.getKey();
                results.add(new VectorSearchResult(
                    id,
                    documents.get(id),
                    entry.getValue(),
                    1.0,
                    metadatas.getOrDefault(id, Map.of())
                ));
            }

            return results;
        }

        void delete(String id) {
            vectors.remove(id);
            documents.remove(id);
            metadatas.remove(id);
        }

        void clear() {
            vectors.clear();
            documents.clear();
            metadatas.clear();
        }

        private float cosineSimilarity(float[] a, float[] b) {
            float dot = 0, normA = 0, normB = 0;
            for (int i = 0; i < a.length; i++) {
                dot += a[i] * b[i];
                normA += a[i] * a[i];
                normB += b[i] * b[i];
            }
            if (normA == 0 || normB == 0) return 0;
            return (float) (dot / (Math.sqrt(normA) * Math.sqrt(normB)));
        }
    }

    /**
     * Entry stored in VectorMemoryStore (Retrieved Memory).
     */
    private static class ArchivedMemoryEntry {
        private final String id;
        private final String content;
        private final String category;
        private final double importance;
        private final LocalDateTime createdAt;
        private LocalDateTime lastAccessed;
        private int accessCount = 0;

        ArchivedMemoryEntry(String id, String content, String category, double importance, LocalDateTime createdAt) {
            this.id = id;
            this.content = content;
            this.category = category;
            this.importance = importance;
            this.createdAt = createdAt;
            this.lastAccessed = null;
        }

        /**
         * Calculate Retrieval Strength.
         *
         * Based on Bjork's New Theory of Disuse:
         * - Time decay: older entries decay but never below min_strength
         * - Access bonus: frequently accessed entries get bonus
         */
        double calculateRetrievalStrength(double decayLambda, double minStrength) {
            // Calculate days idle
            LocalDateTime reference = lastAccessed != null ? lastAccessed : createdAt;
            long daysIdle = ChronoUnit.DAYS.between(reference, LocalDateTime.now());

            // Time decay factor (never below min_strength)
            double timeDecay = minStrength + (1 - minStrength) * Math.exp(-decayLambda * daysIdle);

            // Access bonus factor
            double accessBonus = 1 + 0.5 * Math.log(1 + accessCount);

            return timeDecay * accessBonus;
        }

        void touch() {
            this.lastAccessed = LocalDateTime.now();
            this.accessCount++;
        }
    }
}
