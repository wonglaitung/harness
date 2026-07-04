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

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * Take a screenshot of the page or a specific element.
 *
 * <p>Returns the path to the screenshot file and optionally base64 encoded image.</p>
 */
public class BrowserScreenshotTool implements Tool {

    private static final Logger logger = LoggerFactory.getLogger(BrowserScreenshotTool.class);

    public static final String NAME = "browser_screenshot";

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public String description() {
        return "Take a screenshot of the current page or a specific element.";
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "selector", Map.of(
                    "type", "string",
                    "description", "CSS selector or XPath for a specific element (optional, full page if not specified)"
                ),
                "full_page", Map.of(
                    "type", "boolean",
                    "description", "Capture full scrollable page (default: false)"
                ),
                "return_base64", Map.of(
                    "type", "boolean",
                    "description", "Return base64 encoded image in metadata (default: false)"
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
            String selector = args.containsKey("selector") ? (String) args.get("selector") : null;
            boolean fullPage = args.containsKey("full_page") && (Boolean) args.get("full_page");
            boolean returnBase64 = args.containsKey("return_base64") && (Boolean) args.get("return_base64");

            try {
                Page page = BrowserManager.getPage();

                String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
                String filename = "screenshot_" + timestamp + ".png";

                Path screenshotDir = Path.of(System.getProperty("java.io.tmpdir"), "browser_screenshots");
                Files.createDirectories(screenshotDir);
                Path screenshotPath = screenshotDir.resolve(filename);

                byte[] screenshotBytes;

                if (selector != null && !selector.isBlank()) {
                    // Screenshot specific element
                    boolean isXPath = selector.startsWith("//") || selector.startsWith("(");
                    Locator locator = isXPath
                        ? page.locator("xpath=" + selector)
                        : page.locator(selector);

                    screenshotBytes = locator.screenshot(new Locator.ScreenshotOptions()
                        .setPath(screenshotPath));
                } else {
                    // Screenshot full page or viewport
                    screenshotBytes = page.screenshot(new Page.ScreenshotOptions()
                        .setPath(screenshotPath)
                        .setFullPage(fullPage));
                }

                StringBuilder content = new StringBuilder();
                content.append("✅ Screenshot captured\n");
                content.append("Path: ").append(screenshotPath).append("\n");
                content.append("Full page: ").append(fullPage).append("\n");
                content.append("Size: ").append(screenshotBytes.length).append(" bytes");

                Map<String, Object> metadata = new java.util.HashMap<>();
                metadata.put("path", screenshotPath.toString());
                metadata.put("full_page", fullPage);
                metadata.put("size_bytes", screenshotBytes.length);

                if (returnBase64) {
                    metadata.put("base64", Base64.getEncoder().encodeToString(screenshotBytes));
                }

                return ToolResult.success("", content.toString(), NAME, metadata);

            } catch (Exception e) {
                logger.error("Screenshot failed: {}", e.getMessage(), e);
                return ToolResult.failure("", "Screenshot failed: " + e.getMessage(), NAME);
            }
        });
    }
}
