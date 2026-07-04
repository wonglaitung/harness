package com.harness.tools.browser;

import com.harness.core.Tool;
import com.harness.core.ToolCategory;
import com.harness.core.ToolContext;
import com.harness.core.ValidationResult;
import com.harness.types.ToolResult;
import com.microsoft.playwright.Page;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * Navigate to a URL.
 *
 * <p>Waits for the page to load before returning.</p>
 */
public class BrowserNavigateTool implements Tool {

    private static final Logger logger = LoggerFactory.getLogger(BrowserNavigateTool.class);

    public static final String NAME = "browser_navigate";

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public String description() {
        return "Navigate to a URL and wait for the page to load.";
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "url", Map.of(
                    "type", "string",
                    "description", "URL to navigate to (e.g., 'https://example.com')"
                ),
                "wait_until", Map.of(
                    "type", "string",
                    "enum", List.of("load", "domcontentloaded", "networkidle"),
                    "description", "Wait condition: 'load' (default), 'domcontentloaded', or 'networkidle'"
                ),
                "timeout", Map.of(
                    "type", "integer",
                    "description", "Timeout in milliseconds (default: 30000)"
                )
            ),
            "required", List.of("url")
        );
    }

    @Override
    public ToolCategory category() {
        return ToolCategory.BROWSER;
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
        return ValidationResult.valid();
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        return CompletableFuture.supplyAsync(() -> {
            String url = (String) args.get("url");
            String waitUntil = (String) args.getOrDefault("wait_until", "load");
            int timeout = args.containsKey("timeout") ? ((Number) args.get("timeout")).intValue() : 30000;

            try {
                Page page = BrowserManager.getPage();
                long startTime = System.currentTimeMillis();

                Page.NavigateOptions options = new Page.NavigateOptions()
                    .setWaitUntil(Page.NavigateOptions.WaitUntil.valueOf(waitUntil.toUpperCase()))
                    .setTimeout(timeout);

                page.navigate(url, options);

                long elapsed = System.currentTimeMillis() - startTime;
                String title = page.title();

                StringBuilder content = new StringBuilder();
                content.append("✅ Navigate: ").append(url).append("\n");
                content.append("Title: ").append(title).append("\n");
                content.append("Wait: ").append(waitUntil).append("\n");
                content.append("Time: ").append(String.format("%.2fs", elapsed / 1000.0));

                // Auto screenshot
                String screenshotPath = null;
                if (BrowserManager.getInstance().isAutoScreenshot()) {
                    screenshotPath = BrowserManager.takeScreenshot("navigate");
                    if (screenshotPath != null) {
                        content.append("\nScreenshot: ").append(screenshotPath);
                    }
                }

                return ToolResult.success("", content.toString(), NAME, Map.of(
                    "url", url,
                    "title", title,
                    "elapsed_ms", elapsed,
                    "screenshot_path", screenshotPath != null ? screenshotPath : ""
                ));

            } catch (Exception e) {
                logger.error("Navigate failed: {}", e.getMessage(), e);
                return ToolResult.failure("", "Navigate failed: " + e.getMessage(), NAME);
            }
        });
    }
}
