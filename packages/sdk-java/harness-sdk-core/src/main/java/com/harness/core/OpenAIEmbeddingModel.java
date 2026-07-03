package com.harness.core;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * OpenAI Embedding model implementation.
 *
 * <p>Uses OpenAI's text-embedding-3-small/large or compatible APIs
 * to generate embeddings for semantic search.</p>
 *
 * <h2>Example</h2>
 * <pre>{@code
 * OpenAIEmbeddingModel model = new OpenAIEmbeddingModel(
 *     "sk-...",
 *     "text-embedding-3-small"
 * );
 *
 * float[] embedding = model.embed("Hello world");
 * System.out.println("Dimension: " + embedding.length);
 * }</pre>
 *
 * <h2>Custom Base URL</h2>
 * <pre>{@code
 * OpenAIEmbeddingModel model = new OpenAIEmbeddingModel(
 *     "your-api-key",
 *     "text-embedding-3-small",
 *     "https://your-gateway.com/v1"
 * );
 * }</pre>
 */
public class OpenAIEmbeddingModel implements EmbeddingModel {

    private static final Logger logger = LoggerFactory.getLogger(OpenAIEmbeddingModel.class);
    private static final ObjectMapper MAPPER = new ObjectMapper();

    private final String apiKey;
    private final String model;
    private final String baseUrl;
    private final HttpClient httpClient;
    private final int dimension;

    // Model dimensions mapping
    private static final Map<String, Integer> MODEL_DIMENSIONS = Map.of(
        "text-embedding-3-small", 1536,
        "text-embedding-3-large", 3072,
        "text-embedding-ada-002", 1536
    );

    /**
     * Create OpenAI embedding model with API key.
     *
     * @param apiKey OpenAI API key
     * @param model Model name (e.g., "text-embedding-3-small")
     */
    public OpenAIEmbeddingModel(String apiKey, String model) {
        this(apiKey, model, "https://api.openai.com/v1");
    }

    /**
     * Create OpenAI embedding model with custom base URL.
     *
     * @param apiKey API key
     * @param model Model name
     * @param baseUrl API base URL (for custom gateways)
     */
    public OpenAIEmbeddingModel(String apiKey, String model, String baseUrl) {
        this.apiKey = apiKey;
        this.model = model;
        this.baseUrl = baseUrl;
        this.httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(30))
            .build();
        this.dimension = MODEL_DIMENSIONS.getOrDefault(model, 1536);

        logger.info("OpenAIEmbeddingModel initialized: model={}, dimension={}", model, dimension);
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
            // Build request body
            String requestBody = MAPPER.writeValueAsString(Map.of(
                "input", text,
                "model", model
            ));

            HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/embeddings"))
                .header("Content-Type", "application/json")
                .header("Authorization", "Bearer " + apiKey)
                .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                .timeout(Duration.ofSeconds(60))
                .build();

            HttpResponse<String> response = httpClient.send(request,
                HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() != 200) {
                logger.error("OpenAI embedding API error: {} - {}",
                    response.statusCode(), response.body());
                throw new RuntimeException("Embedding API error: " + response.statusCode());
            }

            // Parse response
            JsonNode root = MAPPER.readTree(response.body());
            JsonNode data = root.path("data");

            if (data.isArray() && data.size() > 0) {
                JsonNode embeddingNode = data.get(0).path("embedding");
                return parseFloatArray(embeddingNode);
            }

            throw new RuntimeException("No embedding in response");

        } catch (IOException | InterruptedException e) {
            logger.error("Failed to get embedding: {}", e.getMessage());
            if (e instanceof InterruptedException) {
                Thread.currentThread().interrupt();
            }
            throw new RuntimeException("Embedding failed", e);
        }
    }

    @Override
    public List<float[]> embedBatch(List<String> texts) {
        if (texts == null || texts.isEmpty()) {
            return new ArrayList<>();
        }

        try {
            // Build request body
            String requestBody = MAPPER.writeValueAsString(Map.of(
                "input", texts,
                "model", model
            ));

            HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/embeddings"))
                .header("Content-Type", "application/json")
                .header("Authorization", "Bearer " + apiKey)
                .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                .timeout(Duration.ofSeconds(120))
                .build();

            HttpResponse<String> response = httpClient.send(request,
                HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() != 200) {
                logger.error("OpenAI embedding batch API error: {} - {}",
                    response.statusCode(), response.body());
                throw new RuntimeException("Embedding API error: " + response.statusCode());
            }

            // Parse response
            JsonNode root = MAPPER.readTree(response.body());
            JsonNode dataArray = root.path("data");

            List<float[]> embeddings = new ArrayList<>();

            // Sort by index (API may return in different order)
            List<JsonNode> sortedData = new ArrayList<>();
            for (JsonNode node : dataArray) {
                sortedData.add(node);
            }
            sortedData.sort((a, b) -> {
                int idxA = a.path("index").asInt();
                int idxB = b.path("index").asInt();
                return Integer.compare(idxA, idxB);
            });

            for (JsonNode data : sortedData) {
                JsonNode embeddingNode = data.path("embedding");
                embeddings.add(parseFloatArray(embeddingNode));
            }

            return embeddings;

        } catch (IOException | InterruptedException e) {
            logger.error("Failed to get batch embeddings: {}", e.getMessage());
            if (e instanceof InterruptedException) {
                Thread.currentThread().interrupt();
            }
            throw new RuntimeException("Batch embedding failed", e);
        }
    }

    @Override
    public boolean isAvailable() {
        return apiKey != null && !apiKey.isEmpty();
    }

    @Override
    public String getName() {
        return "openai-" + model;
    }

    /**
     * Parse JSON array to float array.
     */
    private float[] parseFloatArray(JsonNode node) {
        if (!node.isArray()) {
            return new float[dimension];
        }

        float[] result = new float[node.size()];
        for (int i = 0; i < node.size(); i++) {
            result[i] = (float) node.get(i).asDouble();
        }

        return result;
    }
}
