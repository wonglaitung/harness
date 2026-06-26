package com.harness.tools;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.regex.Pattern;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.core.Tool;
import com.harness.core.ToolCategory;
import com.harness.core.ToolContext;
import com.harness.core.ValidationResult;
import com.harness.types.ToolResult;

/**
 * Web fetch tool for retrieving content from URLs.
 *
 * Fetches web pages and extracts text content.
 *
 * Example:
 * <pre>
 * WebFetchTool tool = new WebFetchTool();
 * ToolResult result = tool.execute(Map.of("url", "https://example.com")).join();
 * </pre>
 */
public class WebFetchTool implements Tool {

    private static final Logger logger = LoggerFactory.getLogger(WebFetchTool.class);

    public static final String NAME = "web_fetch";

    private static final int DEFAULT_MAX_LENGTH = 10000;
    private static final int TIMEOUT_SECONDS = 30;

    private static final Pattern SCRIPT_PATTERN = Pattern.compile(
        "<script[^>]*>.*?</script>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL
    );
    private static final Pattern STYLE_PATTERN = Pattern.compile(
        "<style[^>]*>.*?</style>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL
    );
    private static final Pattern TAG_PATTERN = Pattern.compile("<[^>]+>");
    private static final Pattern WHITESPACE_PATTERN = Pattern.compile("\\s+");

    private final HttpClient client;

    public WebFetchTool() {
        this.client = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(TIMEOUT_SECONDS))
            .followRedirects(HttpClient.Redirect.NORMAL)
            .build();
    }

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public String description() {
        return "Fetch and extract text content from a URL. Returns cleaned text without HTML tags.";
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "url", Map.of(
                    "type", "string",
                    "description", "URL to fetch"
                ),
                "max_length", Map.of(
                    "type", "integer",
                    "description", "Maximum content length in characters (default 10000)",
                    "default", DEFAULT_MAX_LENGTH
                )
            ),
            "required", List.of("url")
        );
    }

    @Override
    public ToolCategory category() {
        return ToolCategory.NETWORK;
    }

    @Override
    public ValidationResult validate(Map<String, Object> args) {
        if (!args.containsKey("url")) {
            return ValidationResult.invalid("url is required");
        }

        String url = (String) args.get("url");
        if (url == null || url.isBlank()) {
            return ValidationResult.invalid("url cannot be empty");
        }

        try {
            URI.create(url);
        } catch (IllegalArgumentException e) {
            return ValidationResult.invalid("Invalid URL format: " + url);
        }

        return ValidationResult.valid();
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        String url = (String) args.get("url");
        int maxLength = args.containsKey("max_length")
            ? ((Number) args.get("max_length")).intValue()
            : DEFAULT_MAX_LENGTH;

        return CompletableFuture.supplyAsync(() -> {
            try {
                HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .timeout(Duration.ofSeconds(TIMEOUT_SECONDS))
                    .header("User-Agent", "Mozilla/5.0 (compatible; HarnessBot/1.0)")
                    .header("Accept", "text/html,application/xhtml+xml")
                    .GET()
                    .build();

                HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

                if (response.statusCode() != 200) {
                    return ToolResult.failure("", "Fetch failed: HTTP " + response.statusCode(), NAME);
                }

                String html = response.body();
                String text = extractText(html);

                // Truncate if needed
                if (text.length() > maxLength) {
                    text = text.substring(0, maxLength) + "\n\n... (truncated)";
                }

                return ToolResult.success("", text, NAME);

            } catch (java.net.http.HttpTimeoutException e) {
                logger.error("Fetch request timed out: {}", url);
                return ToolResult.failure("", "Fetch request timed out", NAME);
            } catch (Exception e) {
                logger.error("Fetch failed: {}", e.getMessage());
                return ToolResult.failure("", "Fetch failed: " + e.getMessage(), NAME);
            }
        });
    }

    /**
     * Extract text from HTML using simple regex-based approach.
     *
     * For more sophisticated parsing, consider using Jsoup library.
     */
    private String extractText(String html) {
        // Remove script and style elements
        String text = SCRIPT_PATTERN.matcher(html).replaceAll("");
        text = STYLE_PATTERN.matcher(text).replaceAll("");

        // Remove all HTML tags
        text = TAG_PATTERN.matcher(text).replaceAll(" ");

        // Clean up whitespace
        text = WHITESPACE_PATTERN.matcher(text).replaceAll(" ").trim();

        // Add newlines after common block elements (simplified)
        text = text.replace(". ", ".\n");
        text = text.replace("? ", "?\n");
        text = text.replace("! ", "!\n");

        return text;
    }
}
