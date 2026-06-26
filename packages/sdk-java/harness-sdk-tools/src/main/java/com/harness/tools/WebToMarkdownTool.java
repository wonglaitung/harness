package com.harness.tools;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.harness.core.Tool;
import com.harness.core.ToolCategory;
import com.harness.core.ToolContext;
import com.harness.core.ValidationResult;
import com.harness.types.ToolResult;

/**
 * Web to Markdown conversion tool.
 *
 * Fetches a webpage and converts it to clean Markdown format.
 * Uses regex-based parsing for lightweight conversion.
 *
 * Example:
 * <pre>
 * WebToMarkdownTool tool = new WebToMarkdownTool();
 * ToolResult result = tool.execute(Map.of("url", "https://example.com")).join();
 * </pre>
 */
public class WebToMarkdownTool implements Tool {

    private static final Logger logger = LoggerFactory.getLogger(WebToMarkdownTool.class);

    public static final String NAME = "web_to_markdown";

    private static final int DEFAULT_MAX_LENGTH = 50000;
    private static final int TIMEOUT_SECONDS = 30;

    // HTML patterns for conversion
    private static final Pattern TITLE_PATTERN = Pattern.compile("<title[^>]*>(.*?)</title>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
    private static final Pattern SCRIPT_PATTERN = Pattern.compile("<script[^>]*>.*?</script>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
    private static final Pattern STYLE_PATTERN = Pattern.compile("<style[^>]*>.*?</style>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
    private static final Pattern NAV_PATTERN = Pattern.compile("<nav[^>]*>.*?</nav>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
    private static final Pattern FOOTER_PATTERN = Pattern.compile("<footer[^>]*>.*?</footer>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
    private static final Pattern HEADER_PATTERN = Pattern.compile("<header[^>]*>.*?</header>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
    private static final Pattern ASIDE_PATTERN = Pattern.compile("<aside[^>]*>.*?</aside>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);

    private static final Pattern H1_PATTERN = Pattern.compile("<h1[^>]*>(.*?)</h1>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
    private static final Pattern H2_PATTERN = Pattern.compile("<h2[^>]*>(.*?)</h2>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
    private static final Pattern H3_PATTERN = Pattern.compile("<h3[^>]*>(.*?)</h3>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
    private static final Pattern H4_PATTERN = Pattern.compile("<h4[^>]*>(.*?)</h4>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
    private static final Pattern H5_PATTERN = Pattern.compile("<h5[^>]*>(.*?)</h5>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
    private static final Pattern H6_PATTERN = Pattern.compile("<h6[^>]*>(.*?)</h6>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);

    private static final Pattern STRONG_PATTERN = Pattern.compile("<(strong|b)[^>]*>(.*?)</\\1>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
    private static final Pattern EM_PATTERN = Pattern.compile("<(em|i)[^>]*>(.*?)</\\1>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
    private static final Pattern CODE_PATTERN = Pattern.compile("<code[^>]*>(.*?)</code>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
    private static final Pattern PRE_PATTERN = Pattern.compile("<pre[^>]*>(.*?)</pre>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
    private static final Pattern BLOCKQUOTE_PATTERN = Pattern.compile("<blockquote[^>]*>(.*?)</blockquote>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);

    private static final Pattern A_PATTERN = Pattern.compile("<a[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
    private static final Pattern IMG_PATTERN = Pattern.compile("<img[^>]*src=\"([^\"]+)\"[^>]*alt=\"([^\"]*)\"[^>]*>", Pattern.CASE_INSENSITIVE);

    private static final Pattern LI_PATTERN = Pattern.compile("<li[^>]*>(.*?)</li>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
    private static final Pattern UL_PATTERN = Pattern.compile("<ul[^>]*>(.*?)</ul>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
    private static final Pattern OL_PATTERN = Pattern.compile("<ol[^>]*>(.*?)</ol>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);

    private static final Pattern P_PATTERN = Pattern.compile("<p[^>]*>(.*?)</p>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL);
    private static final Pattern BR_PATTERN = Pattern.compile("<br\\s*/?>", Pattern.CASE_INSENSITIVE);
    private static final Pattern HR_PATTERN = Pattern.compile("<hr\\s*/?>", Pattern.CASE_INSENSITIVE);

    private static final Pattern DIV_PATTERN = Pattern.compile("</div>", Pattern.CASE_INSENSITIVE);
    private static final Pattern TAG_PATTERN = Pattern.compile("<[^>]+>");
    private static final Pattern WHITESPACE_PATTERN = Pattern.compile("\\s+");

    private final HttpClient client;

    public WebToMarkdownTool() {
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
        return "Fetch a webpage and convert it to clean Markdown format. Preserves headings, lists, code blocks, and links.";
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "url", Map.of(
                    "type", "string",
                    "description", "URL of the webpage to fetch and convert"
                ),
                "max_length", Map.of(
                    "type", "integer",
                    "description", "Maximum content length in characters (default 50000)",
                    "default", DEFAULT_MAX_LENGTH
                ),
                "include_links", Map.of(
                    "type", "boolean",
                    "description", "Whether to preserve links (default true)",
                    "default", true
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
        boolean includeLinks = !args.containsKey("include_links") || (boolean) args.get("include_links");

        return CompletableFuture.supplyAsync(() -> {
            try {
                HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .timeout(Duration.ofSeconds(TIMEOUT_SECONDS))
                    .header("User-Agent", "Mozilla/5.0 (compatible; HarnessBot/1.0; +https://github.com/harness)")
                    .header("Accept", "text/html,application/xhtml+xml")
                    .GET()
                    .build();

                HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());

                if (response.statusCode() != 200) {
                    return ToolResult.failure("", "Fetch failed: HTTP " + response.statusCode(), NAME);
                }

                String html = response.body();
                String markdown = convertToMarkdown(html, includeLinks);

                // Add source URL
                markdown = "[Source](" + url + ")\n\n" + markdown;

                // Truncate if needed
                if (markdown.length() > maxLength) {
                    markdown = markdown.substring(0, maxLength) + "\n\n... (truncated)";
                }

                return ToolResult.success("", markdown, NAME);

            } catch (java.net.http.HttpTimeoutException e) {
                logger.error("Fetch request timed out: {}", url);
                return ToolResult.failure("", "Fetch request timed out", NAME);
            } catch (Exception e) {
                logger.error("Conversion failed: {}", e.getMessage());
                return ToolResult.failure("", "Conversion failed: " + e.getMessage(), NAME);
            }
        });
    }

    /**
     * Convert HTML to Markdown using regex-based approach.
     */
    private String convertToMarkdown(String html, boolean includeLinks) {
        String text = html;

        // Extract title first
        String title = "";
        Matcher titleMatcher = TITLE_PATTERN.matcher(text);
        if (titleMatcher.find()) {
            title = "# " + cleanText(titleMatcher.group(1)) + "\n\n";
            text = TITLE_PATTERN.matcher(text).replaceAll("");
        }

        // Remove unwanted elements
        text = SCRIPT_PATTERN.matcher(text).replaceAll("");
        text = STYLE_PATTERN.matcher(text).replaceAll("");
        text = NAV_PATTERN.matcher(text).replaceAll("");
        text = FOOTER_PATTERN.matcher(text).replaceAll("");
        text = HEADER_PATTERN.matcher(text).replaceAll("");
        text = ASIDE_PATTERN.matcher(text).replaceAll("");

        // Convert headings
        text = H1_PATTERN.matcher(text).replaceAll("\n\n# $1\n\n");
        text = H2_PATTERN.matcher(text).replaceAll("\n\n## $1\n\n");
        text = H3_PATTERN.matcher(text).replaceAll("\n\n### $1\n\n");
        text = H4_PATTERN.matcher(text).replaceAll("\n\n#### $1\n\n");
        text = H5_PATTERN.matcher(text).replaceAll("\n\n##### $1\n\n");
        text = H6_PATTERN.matcher(text).replaceAll("\n\n###### $1\n\n");

        // Convert text formatting
        text = STRONG_PATTERN.matcher(text).replaceAll("**$2**");
        text = EM_PATTERN.matcher(text).replaceAll("*$2*");

        // Convert code blocks
        text = PRE_PATTERN.matcher(text).replaceAll("\n\n```\n$1\n```\n\n");
        text = CODE_PATTERN.matcher(text).replaceAll("`$1`");

        // Convert blockquotes
        text = BLOCKQUOTE_PATTERN.matcher(text).replaceAll("\n\n> $1\n\n");

        // Convert links
        if (includeLinks) {
            text = A_PATTERN.matcher(text).replaceAll("[$2]($1)");
        } else {
            text = A_PATTERN.matcher(text).replaceAll("$2");
        }

        // Convert images
        text = IMG_PATTERN.matcher(text).replaceAll("![$2]($1)");

        // Convert paragraphs
        text = P_PATTERN.matcher(text).replaceAll("\n\n$1\n\n");
        text = BR_PATTERN.matcher(text).replaceAll("\n");
        text = HR_PATTERN.matcher(text).replaceAll("\n\n---\n\n");

        // Convert lists
        text = convertLists(text);

        // Clean up remaining tags
        text = DIV_PATTERN.matcher(text).replaceAll("\n");
        text = TAG_PATTERN.matcher(text).replaceAll("");

        // Clean up whitespace
        text = WHITESPACE_PATTERN.matcher(text).replaceAll(" ");
        text = text.replaceAll("\\n\\s+\\n", "\n\n");
        text = text.replaceAll("(\\n){3,}", "\n\n");
        text = text.trim();

        return title + text;
    }

    /**
     * Convert HTML lists to Markdown format.
     */
    private String convertLists(String text) {
        // Convert unordered lists
        StringBuilder result = new StringBuilder();
        Matcher ulMatcher = UL_PATTERN.matcher(text);

        while (ulMatcher.find()) {
            String listContent = ulMatcher.group(1);
            StringBuilder listMd = new StringBuilder("\n\n");

            Matcher liMatcher = LI_PATTERN.matcher(listContent);
            while (liMatcher.find()) {
                String item = cleanText(liMatcher.group(1));
                listMd.append("- ").append(item).append("\n");
            }

            ulMatcher.appendReplacement(result, listMd.toString());
        }
        ulMatcher.appendTail(result);

        // Convert ordered lists
        text = result.toString();
        result = new StringBuilder();
        Matcher olMatcher = OL_PATTERN.matcher(text);

        while (olMatcher.find()) {
            String listContent = olMatcher.group(1);
            StringBuilder listMd = new StringBuilder("\n\n");

            Matcher liMatcher = LI_PATTERN.matcher(listContent);
            int count = 1;
            while (liMatcher.find()) {
                String item = cleanText(liMatcher.group(1));
                listMd.append(count++).append(". ").append(item).append("\n");
            }

            olMatcher.appendReplacement(result, listMd.toString());
        }
        olMatcher.appendTail(result);

        return result.toString();
    }

    /**
     * Clean text by removing extra whitespace and HTML entities.
     */
    private String cleanText(String text) {
        text = TAG_PATTERN.matcher(text).replaceAll("");
        text = WHITESPACE_PATTERN.matcher(text).replaceAll(" ").trim();

        // Decode common HTML entities
        text = text.replace("&amp;", "&");
        text = text.replace("&lt;", "<");
        text = text.replace("&gt;", ">");
        text = text.replace("&quot;", "\"");
        text = text.replace("&#39;", "'");

        return text;
    }
}
