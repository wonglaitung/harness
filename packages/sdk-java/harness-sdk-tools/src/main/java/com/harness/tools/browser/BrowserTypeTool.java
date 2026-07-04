package com.harness.tools.browser;

import com.harness.core.Tool;
import com.harness.core.ToolCategory;
import com.harness.core.ToolContext;
import com.harness.core.ValidationResult;
import com.harness.types.ToolResult;
import com.microsoft.playwright.Locator;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.options.WaitForSelectorState;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * Type text into an input field.
 *
 * <p>Waits for the element to be visible, optionally clears existing text first.</p>
 */
public class BrowserTypeTool implements Tool {

    private static final Logger logger = LoggerFactory.getLogger(BrowserTypeTool.class);

    public static final String NAME = "browser_type";

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public String description() {
        return "Type text into an input field. Waits for element to be visible.";
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "selector", Map.of(
                    "type", "string",
                    "description", "CSS selector or XPath for the input field"
                ),
                "text", Map.of(
                    "type", "string",
                    "description", "Text to type"
                ),
                "clear_first", Map.of(
                    "type", "boolean",
                    "description", "Clear existing text before typing (default: true)"
                ),
                "timeout", Map.of(
                    "type", "integer",
                    "description", "Wait timeout in milliseconds (default: 10000)"
                ),
                "delay", Map.of(
                    "type", "integer",
                    "description", "Delay between keystrokes in milliseconds (default: 50)"
                )
            ),
            "required", List.of("selector", "text")
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
        if (!args.containsKey("text")) {
            return ValidationResult.invalid("text is required");
        }
        return ValidationResult.valid();
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        return CompletableFuture.supplyAsync(() -> {
            String selector = (String) args.get("selector");
            String text = (String) args.get("text");
            boolean clearFirst = !args.containsKey("clear_first") || (Boolean) args.get("clear_first");
            int timeout = args.containsKey("timeout") ? ((Number) args.get("timeout")).intValue() : 10000;
            int delay = args.containsKey("delay") ? ((Number) args.get("delay")).intValue() : 50;

            try {
                Page page = BrowserManager.getPage();
                long startTime = System.currentTimeMillis();

                // Determine if XPath
                boolean isXPath = selector.startsWith("//") || selector.startsWith("(");
                Locator locator = isXPath
                    ? page.locator("xpath=" + selector)
                    : page.locator(selector);

                // Wait for element to be visible
                locator.waitFor(new Locator.WaitForOptions()
                    .setState(WaitForSelectorState.VISIBLE)
                    .setTimeout(timeout));

                // Clear existing text if requested
                if (clearFirst) {
                    locator.fill("");
                    logger.debug("Cleared existing text");
                }

                // Type with realistic delay
                locator.type(text, new Locator.TypeOptions().setDelay(delay));

                long elapsed = System.currentTimeMillis() - startTime;

                StringBuilder content = new StringBuilder();
                content.append("✅ Type: ").append(selector).append("\n");
                content.append("Text: ").append(text.length() > 50 ? text.substring(0, 50) + "..." : text).append("\n");
                content.append("Length: ").append(text.length()).append("\n");
                content.append("Time: ").append(elapsed).append("ms");

                // Auto screenshot
                String screenshotPath = null;
                if (BrowserManager.getInstance().isAutoScreenshot()) {
                    screenshotPath = BrowserManager.takeScreenshot("type");
                    if (screenshotPath != null) {
                        content.append("\nScreenshot: ").append(screenshotPath);
                    }
                }

                return ToolResult.success("", content.toString(), NAME, Map.of(
                    "selector", selector,
                    "text_length", text.length(),
                    "elapsed_ms", elapsed,
                    "screenshot_path", screenshotPath != null ? screenshotPath : ""
                ));

            } catch (Exception e) {
                logger.error("Type failed: {}", e.getMessage(), e);
                return ToolResult.failure("", "Type failed: " + e.getMessage(), NAME);
            }
        });
    }
}
