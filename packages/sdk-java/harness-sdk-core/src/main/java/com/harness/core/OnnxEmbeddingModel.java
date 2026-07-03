package com.harness.core;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import ai.onnxruntime.OnnxTensor;
import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtException;
import ai.onnxruntime.OrtSession;

/**
 * ONNX-based local embedding model.
 *
 * <p>Uses ONNX Runtime with sentence-transformers models for
 * local, offline-capable embedding generation.</p>
 *
 * <h2>Supported Models</h2>
 * <ul>
 *   <li>all-MiniLM-L6-v2 (384 dims, fast, good quality)</li>
 *   <li>all-mpnet-base-v2 (768 dims, slower, best quality)</li>
 *   <li>paraphrase-multilingual-MiniLM-L12-v2 (384 dims, multilingual)</li>
 * </ul>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * // Download model from HuggingFace and convert to ONNX
 * // https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
 *
 * OnnxEmbeddingModel model = new OnnxEmbeddingModel(
 *     Path.of("models/all-MiniLM-L6-v2.onnx"),
 *     384
 * );
 *
 * float[] embedding = model.embed("Hello world");
 * }</pre>
 *
 * <h2>Model Preparation</h2>
 * <p>Convert sentence-transformers model to ONNX:</p>
 * <pre>
 * python -c "
 * from transformers import AutoModel, AutoTokenizer
 * from optimum.exporters.onnx import main_export
 *
 * model_id = 'sentence-transformers/all-MiniLM-L6-v2'
 * main_export(model_id, output='models/all-MiniLM-L6-v2')
 * "
 * </pre>
 */
public class OnnxEmbeddingModel implements EmbeddingModel {

    private static final Logger logger = LoggerFactory.getLogger(OnnxEmbeddingModel.class);

    private final Path modelPath;
    private final int dimension;
    private final OrtEnvironment env;
    private final OrtSession session;
    private final Tokenizer tokenizer;
    private final boolean normalizeEmbeddings;

    // Cache for tokenization
    private final Map<String, long[]> tokenCache = new ConcurrentHashMap<>();
    private static final int MAX_CACHE_SIZE = 10000;

    /**
     * Create ONNX embedding model.
     *
     * @param modelPath Path to ONNX model file
     * @param dimension Embedding dimension
     * @throws IOException If model cannot be loaded
     */
    public OnnxEmbeddingModel(Path modelPath, int dimension) throws IOException {
        this(modelPath, dimension, true);
    }

    /**
     * Create ONNX embedding model with normalization option.
     *
     * @param modelPath Path to ONNX model file
     * @param dimension Embedding dimension
     * @param normalize Whether to L2-normalize embeddings
     * @throws IOException If model cannot be loaded
     */
    public OnnxEmbeddingModel(Path modelPath, int dimension, boolean normalize) throws IOException {
        this.modelPath = modelPath;
        this.dimension = dimension;
        this.normalizeEmbeddings = normalize;

        if (!Files.exists(modelPath)) {
            throw new IOException("Model file not found: " + modelPath);
        }

        try {
            this.env = OrtEnvironment.getEnvironment();
            this.session = env.createSession(modelPath.toString());

            logger.info("ONNX model loaded: {} (dimension={})", modelPath, dimension);

        } catch (OrtException e) {
            throw new IOException("Failed to load ONNX model: " + e.getMessage(), e);
        }

        // Initialize simple tokenizer (WordPiece-like)
        this.tokenizer = new SimpleTokenizer();
    }

    @Override
    public int getDimension() {
        return dimension;
    }

    @Override
    public float[] embed(String text) {
        if (text == null || text.isEmpty()) {
            return new float[dimension];
        }

        try {
            // Tokenize
            long[] inputIds = tokenize(text);

            // Create input tensors
            long[] shape = {1, inputIds.length};
            OnnxTensor inputTensor = OnnxTensor.createTensor(env, new long[][]{inputIds});

            // Run inference
            OrtSession.Result result = session.run(Map.of("input_ids", inputTensor));

            // Get output (last_hidden_state or sentence_embedding)
            float[][][] output = (float[][][]) result.get(0).getValue();

            // Mean pooling over tokens (simplified - use CLS token for some models)
            float[] embedding = meanPool(output[0]);

            // Normalize if requested
            if (normalizeEmbeddings) {
                embedding = normalize(embedding);
            }

            // Cleanup
            inputTensor.close();
            result.close();

            return embedding;

        } catch (OrtException e) {
            logger.error("ONNX inference error: {}", e.getMessage());
            throw new RuntimeException("Embedding inference failed", e);
        }
    }

    @Override
    public List<float[]> embedBatch(List<String> texts) {
        if (texts == null || texts.isEmpty()) {
            return new ArrayList<>();
        }

        List<float[]> embeddings = new ArrayList<>();

        // Process in batches (ONNX typically handles one at a time for simplicity)
        for (String text : texts) {
            embeddings.add(embed(text));
        }

        return embeddings;
    }

    @Override
    public boolean isAvailable() {
        return session != null;
    }

    @Override
    public String getName() {
        return "onnx-" + modelPath.getFileName().toString();
    }

    /**
     * Close the model and release resources.
     */
    public void close() {
        try {
            if (session != null) {
                session.close();
            }
            tokenCache.clear();
            logger.info("ONNX model closed: {}", modelPath);
        } catch (Exception e) {
            logger.warn("Error closing ONNX session: {}", e.getMessage());
        }
    }

    /**
     * Tokenize text to input IDs.
     */
    private long[] tokenize(String text) {
        // Check cache
        if (tokenCache.containsKey(text)) {
            return tokenCache.get(text);
        }

        long[] tokens = tokenizer.tokenize(text);

        // Cache management
        if (tokenCache.size() < MAX_CACHE_SIZE) {
            tokenCache.put(text, tokens);
        }

        return tokens;
    }

    /**
     * Mean pooling over token embeddings.
     */
    private float[] meanPool(float[][] tokenEmbeddings) {
        float[] result = new float[dimension];

        for (float[] tokenEmb : tokenEmbeddings) {
            for (int i = 0; i < Math.min(tokenEmb.length, dimension); i++) {
                result[i] += tokenEmb[i];
            }
        }

        // Average
        int numTokens = tokenEmbeddings.length;
        for (int i = 0; i < dimension; i++) {
            result[i] /= numTokens;
        }

        return result;
    }

    /**
     * L2 normalize embedding.
     */
    private float[] normalize(float[] embedding) {
        float norm = 0;
        for (float v : embedding) {
            norm += v * v;
        }
        norm = (float) Math.sqrt(norm);

        if (norm > 0) {
            for (int i = 0; i < embedding.length; i++) {
                embedding[i] /= norm;
            }
        }

        return embedding;
    }

    // -------------------------------------------------------------------------
    // Tokenizer interface and simple implementation
    // -------------------------------------------------------------------------

    /**
     * Simple tokenizer interface.
     */
    public interface Tokenizer {
        long[] tokenize(String text);
    }

    /**
     * Simple whitespace tokenizer with vocabulary.
     * For production, use HuggingFace tokenizers with proper WordPiece/BPE.
     */
    private static class SimpleTokenizer implements Tokenizer {

        // Special tokens
        private static final long CLS_TOKEN = 101;
        private static final long SEP_TOKEN = 102;
        private static final long PAD_TOKEN = 0;
        private static final long UNK_TOKEN = 100;

        // Simple hash-based vocabulary (production: load from vocab.txt)
        private final Map<String, Long> vocab = new ConcurrentHashMap<>();

        SimpleTokenizer() {
            // Initialize with common words (simplified)
            // Production: load vocabulary from model directory
        }

        @Override
        public long[] tokenize(String text) {
            // Normalize
            text = text.toLowerCase().replaceAll("[^a-z0-9\\s]", "");

            // Split by whitespace
            String[] words = text.split("\\s+");

            // Build token IDs
            List<Long> ids = new ArrayList<>();
            ids.add(CLS_TOKEN);

            for (String word : words) {
                if (word.isEmpty()) continue;

                // Get or create token ID
                long tokenId = vocab.getOrDefault(word, hashToTokenId(word));
                ids.add(tokenId);

                // Limit sequence length
                if (ids.size() >= 510) break;
            }

            ids.add(SEP_TOKEN);

            // Convert to array
            long[] result = new long[ids.size()];
            for (int i = 0; i < ids.size(); i++) {
                result[i] = ids.get(i);
            }

            return result;
        }

        /**
         * Deterministic hash to token ID.
         * Production: use actual vocabulary lookup
         */
        private long hashToTokenId(String word) {
            return 1000 + Math.abs(word.hashCode() % 30000);
        }
    }
}
