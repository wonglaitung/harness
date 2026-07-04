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

import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * Click an element on the page.
 *
 * <p>Waits for the element to be visible and clickable before clicking.
 * Retries on transient failures.</p>
 */
public class BrowserClickTool implements Tool {

    private static final Logger logger = LoggerFactory.getLogger(BrowserClickTool.class);

    public static final String NAME = "browser_click";

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public String description() {
        return "Click an element on the page. Waits for element to be visible and clickable.";
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "selector", Map.of(
                    "type", "string",
                    "description", "CSS selector or XPath (e.g., '#submit-btn', '//button[text()=\"Submit\"]')"
                ),
                "timeout", Map.of(
                    "type", "integer",
                    "description", "Wait timeout in milliseconds (default: 10000)"
                ),
                "force", Map.of(
                    "type", "boolean",
                    "description", "Force click even if element is not visible (default: false)"
                ),
                "retry_count", Map.of(
                    "type", "integer",
                    "description", "Number of retries on failure (default: 2)"
                )
            ),
            "required", List.of("selector")
        );
    }

    @Override
    public ToolCategory category() {
        return ToolCategory.NETWORK;
    }

    @Override
    public ValidationResult validate(Map<String, Object> args) {
        if (!args.containsKey("selector")) {
            return ValidationResult.invalid("selector is required");
        }
        return ValidationResult.valid();
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        return CompletableFuture.supplyAsync(() -> {
            String selector = (String) args.get("selector");
            int timeout = args.containsKey("timeout") ? ((Number) args.get("timeout")).intValue() : 10000;
            boolean force = args.containsKey("force") && (Boolean) args.get("force");
            int retryCount = args.containsKey("retry_count") ? ((Number) args.get("retry_count")).intValue() : 2;

            try {
                Page page = BrowserManager.getPage();
                long startTime = System.currentTimeMillis();

                // Determine if XPath
                boolean isXPath = selector.startsWith("//") || selector.startsWith("(");
                Locator locator = isXPath
                    ? page.locator("xpath=" + selector)
                    : page.locator(selector);

                Exception lastError = null;
                int attempts = 0;

                for (int attempt = 0; attempt <= retryCount; attempt++) {
                    attempts = attempt + 1;
                    try {
                        // Wait for element to be visible
                        if (!force) {
                            locator.waitFor(new Locator.WaitForOptions()
                                .setState(Locator.WaitForOptions.State.VISIBLE)
                                .setTimeout(timeout));
                        }

                        locator.click(new Locator.ClickOptions().setForce(force));

                        long elapsed = System.currentTimeMillis() - startTime;

                        StringBuilder content = new StringBuilder();
                        content.append("✅ Click: ").append(selector).append("\n");
                        content.append("Attempts: ").append(attempts).append("\n");
                        content.append("Time: ").append(elapsed).append("ms");

                        // Auto screenshot
                        String screenshotPath = null;
                        if (BrowserManager.getInstance().isAutoScreenshot()) {
                            screenshotPath = BrowserManager.takeScreenshot("click");
                            if (screenshotPath != null) {
                                content.append("\nScreenshot: ").append(screenshotPath);
                            }
                        }

                        return ToolResult.success("", content.toString(), NAME, Map.of(
                            "selector", selector,
                            "elapsed_ms", elapsed,
                            "attempts", attempts,
                            "screenshot_path", screenshotPath != null ? screenshotPath : ""
                        ));

                    } catch (Exception e) {
                        lastError = e;
                        if (attempt < retryCount) {
                            logger.warn("Click attempt {} failed, retrying: {}", attempt + 1, e.getMessage());
                            try {
                                Thread.sleep(500);
                            } catch (InterruptedException ie) {
                                Thread.currentThread().interrupt();
                            }
                        }
                    }
                }

                throw lastError != null ? lastError : new RuntimeException("Click failed");

            } catch (Exception e) {
                logger.error("Click failed: {}", e.getMessage(), e);
                return ToolResult.failure("", "Click failed: " + e.getMessage(), NAME);
            }
        });
    }
}
