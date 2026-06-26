package com.harness.tools;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.harness.core.Tool;
import com.harness.core.ToolCategory;
import com.harness.core.ToolContext;
import com.harness.core.ValidationResult;
import com.harness.types.ToolResult;

/**
 * Web search tool using DuckDuckGo Instant Answer API.
 *
 * Free, no API key required.
 *
 * Example:
 * <pre>
 * WebSearchTool tool = new WebSearchTool();
 * ToolResult result = tool.execute(Map.of("query", "Java 21 features")).join();
 * </pre>
 */
public class WebSearchTool implements Tool {

    private static final Logger logger = LoggerFactory.getLogger(WebSearchTool.class);

    public static final String NAME = "web_search";

    private static final String API_URL = "https://api.duckduckgo.com/";
    private static final int DEFAULT_NUM_RESULTS = 5;
    private static final int TIMEOUT_SECONDS = 30;

    private final HttpClient client;
    private final ObjectMapper objectMapper;

    public WebSearchTool() {
        this.client = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(TIMEOUT_SECONDS))
            .build();
        this.objectMapper = new ObjectMapper();
    }

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public String description() {
        return "Search the web for information using a search query. Returns instant answers and related topics.";
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "query", Map.of(
                    "type", "string",
                    "description", "Search query"
                ),
                "num_results", Map.of(
                    "type", "integer",
                    "description", "Number of results to return (default 5)",
                    "default", DEFAULT_NUM_RESULTS
                )
            ),
            "required", List.of("query")
        );
    }

    @Override
    public ToolCategory category() {
        return ToolCategory.NETWORK;
    }

    @Override
    public ValidationResult validate(Map<String, Object> args) {
        if (!args.containsKey("query")) {
            return ValidationResult.invalid("query is required");
        }

        String query = (String) args.get("query");
        if (query == null || query.isBlank()) {
            return ValidationResult.invalid("query cannot be empty");
        }

        return ValidationResult.valid();
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        String query = (String) args.get("query");
        int numResults = args.containsKey("num_results")
            ? ((Number) args.get("num_results")).intValue()
            : DEFAULT_NUM_RESULTS;

        return CompletableFuture.supplyAsync(() -> {
            try {
                // Build request URL
                String url = String.format("%s?q=%s&format=json&no_html=1&skip_disambig=1",
                    API_URL,
                    java.net.URLEncoder.encode(query, java.nio.charset.StandardCharsets.UTF_8)
                );

                HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .timeout(Duration.ofSeconds(TIMEOUT_SECONDS))
                    .header("Accept", "application/json")
                    .GET()
                    .build();

                HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

                if (response.statusCode() != 200) {
                    return ToolResult.failure("", "Search failed: HTTP " + response.statusCode(), NAME);
                }

                // Parse response
                JsonNode data = objectMapper.readTree(response.body());
                StringBuilder result = new StringBuilder();

                // Abstract (instant answer)
                if (data.has("Abstract") && !data.get("Abstract").asText().isEmpty()) {
                    result.append("**Answer**: ").append(data.get("Abstract").asText()).append("\n");
                    if (data.has("AbstractURL") && !data.get("AbstractURL").asText().isEmpty()) {
                        result.append("Source: ").append(data.get("AbstractURL").asText()).append("\n");
                    }
                    result.append("\n");
                }

                // Related topics
                JsonNode topics = data.get("RelatedTopics");
                if (topics != null && topics.isArray()) {
                    int count = 0;
                    for (JsonNode topic : topics) {
                        if (count >= numResults) break;

                        if (topic.isObject() && topic.has("Text")) {
                            result.append("- ").append(topic.get("Text").asText()).append("\n");
                            if (topic.has("FirstURL")) {
                                result.append("  URL: ").append(topic.get("FirstURL").asText()).append("\n");
                            }
                            count++;
                        }
                    }
                }

                if (result.length() == 0) {
                    result.append("No results found for: ").append(query);
                }

                return ToolResult.success("", result.toString(), NAME);

            } catch (java.net.http.HttpTimeoutException e) {
                logger.error("Search request timed out: {}", query);
                return ToolResult.failure("", "Search request timed out", NAME);
            } catch (Exception e) {
                logger.error("Search failed: {}", e.getMessage());
                return ToolResult.failure("", "Search failed: " + e.getMessage(), NAME);
            }
        });
    }
}
