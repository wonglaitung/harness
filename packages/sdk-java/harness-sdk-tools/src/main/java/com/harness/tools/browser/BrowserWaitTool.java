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
 * Wait for a condition on the page.
 *
 * <p>Can wait for:</p>
 * <ul>
 *   <li>Element to appear/disappear</li>
 *   <li>URL to change</li>
 *   <li>A timeout</li>
 * </ul>
 */
public class BrowserWaitTool implements Tool {

    private static final Logger logger = LoggerFactory.getLogger(BrowserWaitTool.class);

    public static final String NAME = "browser_wait";

    @Override
    public String name() {
        return NAME;
    }

    @Override
    public String description() {
        return "Wait for a condition on the page (element, URL, or timeout).";
    }

    @Override
    public Map<String, Object> inputSchema() {
        return Map.of(
            "type", "object",
            "properties", Map.of(
                "wait_type", Map.of(
                    "type", "string",
                    "enum", List.of("selector", "url", "timeout"),
                    "description", "What to wait for: 'selector' (element), 'url', or 'timeout'"
                ),
                "selector", Map.of(
                    "type", "string",
                    "description", "CSS selector or XPath (required if wait_type='selector')"
                ),
                "state", Map.of(
                    "type", "string",
                    "enum", List.of("visible", "hidden", "attached", "detached"),
                    "description", "Element state to wait for (default: 'visible')"
                ),
                "url_pattern", Map.of(
                    "type", "string",
                    "description", "URL pattern to wait for (required if wait_type='url')"
                ),
                "timeout_ms", Map.of(
                    "type", "integer",
                    "description", "Timeout in milliseconds (default: 30000)"
                )
            ),
            "required", List.of("wait_type")
        );
    }

    @Override
    public ToolCategory category() {
        return ToolCategory.NETWORK;
    }

    @Override
    public ValidationResult validate(Map<String, Object> args) {
        if (!args.containsKey("wait_type")) {
            return ValidationResult.invalid("wait_type is required");
        }
        String waitType = (String) args.get("wait_type");
        if ("selector".equals(waitType) && !args.containsKey("selector")) {
            return ValidationResult.invalid("selector is required for wait_type='selector'");
        }
        if ("url".equals(waitType) && !args.containsKey("url_pattern")) {
            return ValidationResult.invalid("url_pattern is required for wait_type='url'");
        }
        return ValidationResult.valid();
    }

    @Override
    public CompletableFuture<ToolResult> execute(Map<String, Object> args, ToolContext context) {
        return CompletableFuture.supplyAsync(() -> {
            String waitType = (String) args.get("wait_type");
            int timeoutMs = args.containsKey("timeout_ms") ? ((Number) args.get("timeout_ms")).intValue() : 30000;

            try {
                Page page = BrowserManager.getPage();
                long startTime = System.currentTimeMillis();

                if ("selector".equals(waitType)) {
                    String selector = (String) args.get("selector");
                    String stateStr = args.containsKey("state") ? (String) args.get("state") : "visible";

                    boolean isXPath = selector.startsWith("//") || selector.startsWith("(");
                    Locator locator = isXPath
                        ? page.locator("xpath=" + selector)
                        : page.locator(selector);

                    Locator.WaitForOptions.State state = Locator.WaitForOptions.State.valueOf(stateStr.toUpperCase());
                    locator.waitFor(new Locator.WaitForOptions().setState(state).setTimeout(timeoutMs));

                    long elapsed = System.currentTimeMillis() - startTime;

                    return ToolResult.success("", String.format(
                        "✅ Wait: %s became %s in %dms",
                        selector, stateStr, elapsed
                    ), NAME, Map.of(
                        "wait_type", waitType,
                        "selector", selector,
                        "state", stateStr,
                        "elapsed_ms", elapsed
                    ));

                } else if ("url".equals(waitType)) {
                    String urlPattern = args.containsKey("url_pattern") ? (String) args.get("url_pattern") : "**";
                    page.waitForURL(urlPattern, new Page.WaitForURLOptions().setTimeout(timeoutMs));

                    long elapsed = System.currentTimeMillis() - startTime;

                    return ToolResult.success("", String.format(
                        "✅ Wait: URL matched '%s' in %dms\nCurrent URL: %s",
                        urlPattern, elapsed, page.url()
                    ), NAME, Map.of(
                        "wait_type", waitType,
                        "url_pattern", urlPattern,
                        "current_url", page.url(),
                        "elapsed_ms", elapsed
                    ));

                } else if ("timeout".equals(waitType)) {
                    int timeoutValue = args.containsKey("timeout_ms") ? ((Number) args.get("timeout_ms")).intValue() : 1000;
                    page.waitForTimeout(timeoutValue);

                    long elapsed = System.currentTimeMillis() - startTime;

                    return ToolResult.success("", String.format(
                        "✅ Wait: %dms timeout completed",
                        timeoutValue
                    ), NAME, Map.of(
                        "wait_type", waitType,
                        "timeout_ms", timeoutValue,
                        "elapsed_ms", elapsed
                    ));

                } else {
                    return ToolResult.failure("", "Unknown wait_type: " + waitType, NAME);
                }

            } catch (Exception e) {
                logger.error("Wait failed: {}", e.getMessage(), e);
                return ToolResult.failure("", "Wait failed: " + e.getMessage(), NAME);
            }
        });
    }
}
