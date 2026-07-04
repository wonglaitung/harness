package com.harness.tools.browser;

import com.harness.core.Tool;
import com.harness.core.ToolCategory;
import com.harness.core.ToolContext;
import com.harness.core.ValidationResult;
import com.harness.types.ToolResult;
import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * Extract data from the page.
 *
 * <p>Can extract text content, attributes, or structured data from elements.</p>
 */
public class BrowserExtractTool implements Tool {

    private static final Logger logger = LoggerFactory.getLogger(BrowserExtractTool.class);

    public static final String NAME = "browser_extract";

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public String description() {
        return "Extract text or data from page elements.";
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "selector", Map.of(
                    "type", "string",
                    "description", "CSS selector or XPath for elements to extract (optional, extracts from body if not specified)"
                ),
                "attribute", Map.of(
                    "type", "string",
                    "description", "Attribute to extract (e.g., 'href', 'src'). Extracts text content if not specified."
                ),
                "multiple", Map.of(
                    "type", "boolean",
                    "description", "Extract all matching elements (default: false, extract first only)"
                ),
                "as_markdown", Map.of(
                    "type", "boolean",
                    "description", "Convert extracted content to Markdown (default: false)"
                )
            ),
            "required", List.of()
        );
    }

    @Override
    public ToolCategory category() {
        return ToolCategory.NETWORK;
    }

    @Override
    public ValidationResult validate(Map<String, Object> args) {
        return ValidationResult.valid();
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        return CompletableFuture.supplyAsync(() -> {
            String selector = args.containsKey("selector") ? (String) args.get("selector") : "body";
            String attribute = args.containsKey("attribute") ? (String) args.get("attribute") : null;
            boolean multiple = args.containsKey("multiple") && (Boolean) args.get("multiple");
            boolean asMarkdown = args.containsKey("as_markdown") && (Boolean) args.get("as_markdown");

            try {
                Page page = BrowserManager.getPage();

                // Determine if XPath
                boolean isXPath = selector.startsWith("//") || selector.startsWith("(");
                Locator locator = isXPath
                    ? page.locator("xpath=" + selector)
                    : page.locator(selector);

                List<String> results = new ArrayList<>();

                if (multiple) {
                    int count = locator.count();
                    for (int i = 0; i < count; i++) {
                        Locator element = locator.nth(i);
                        String value = extractValue(element, attribute, asMarkdown);
                        if (value != null && !value.isBlank()) {
                            results.add(value.trim());
                        }
                    }
                } else {
                    String value = extractValue(locator, attribute, asMarkdown);
                    if (value != null && !value.isBlank()) {
                        results.add(value.trim());
                    }
                }

                if (results.isEmpty()) {
                    return ToolResult.success("", "No content extracted (element may be empty or not found)", NAME);
                }

                String content = results.size() > 1
                    ? String.join("\n---\n", results)
                    : results.get(0);

                return ToolResult.success("", content, NAME, Map.of(
                    "selector", selector,
                    "attribute", attribute != null ? attribute : "",
                    "count", results.size(),
                    "multiple", multiple
                ));

            } catch (Exception e) {
                logger.error("Extract failed: {}", e.getMessage(), e);
                return ToolResult.failure("", "Extract failed: " + e.getMessage(), NAME);
            }
        });
    }

    private String extractValue(Locator locator, String attribute, boolean asMarkdown) {
        if (attribute != null) {
            return locator.getAttribute(attribute);
        } else if (asMarkdown) {
            return locator.innerText();
        } else {
            return locator.textContent();
        }
    }
}
