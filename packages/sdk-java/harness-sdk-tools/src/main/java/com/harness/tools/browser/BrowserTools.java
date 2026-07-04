package com.harness.tools.browser;

import com.harness.core.Tool;

import java.util.ArrayList;
import java.util.List;

/**
 * Utility class for browser automation tools.
 *
 * <h2>Browser Types</h2>
 * <ul>
 *   <li>{@code chromium} - Playwright's bundled Chromium (requires {@code playwright install})</li>
 *   <li>{@code firefox} - Playwright's bundled Firefox (requires {@code playwright install})</li>
 *   <li>{@code webkit} - Playwright's bundled WebKit (requires {@code playwright install})</li>
 *   <li>{@code msedge} - System Microsoft Edge (no download needed, ideal for intranet)</li>
 *   <li>{@code chrome} - System Google Chrome (no download needed)</li>
 * </ul>
 *
 * <h2>Usage</h2>
 * <pre>{@code
 * // Configure for intranet (use system Edge)
 * BrowserManager.useSystemBrowser();
 *
 * // Get all browser tools
 * List<Tool> tools = BrowserTools.getAll();
 *
 * // Or get individual tools
 * Tool navigate = BrowserTools.navigate();
 * Tool click = BrowserTools.click();
 * }</pre>
 */
public final class BrowserTools {

    private BrowserTools() {
        // Utility class
    }

    /**
     * Get all browser automation tools.
     *
     * @return List of browser Tool instances
     */
    public static List<Tool> getAll() {
        List<Tool> tools = new ArrayList<>();
        tools.add(navigate());
        tools.add(click());
        tools.add(type());
        tools.add(extract());
        tools.add(screenshot());
        tools.add(waitFor());
        tools.add(close());
        return tools;
    }

    /**
     * Get browser navigate tool.
     */
    public static BrowserNavigateTool navigate() {
        return new BrowserNavigateTool();
    }

    /**
     * Get browser click tool.
     */
    public static BrowserClickTool click() {
        return new BrowserClickTool();
    }

    /**
     * Get browser type tool.
     */
    public static BrowserTypeTool type() {
        return new BrowserTypeTool();
    }

    /**
     * Get browser extract tool.
     */
    public static BrowserExtractTool extract() {
        return new BrowserExtractTool();
    }

    /**
     * Get browser screenshot tool.
     */
    public static BrowserScreenshotTool screenshot() {
        return new BrowserScreenshotTool();
    }

    /**
     * Get browser wait tool.
     */
    public static BrowserWaitTool waitFor() {
        return new BrowserWaitTool();
    }

    /**
     * Get browser close tool.
     */
    public static BrowserCloseTool close() {
        return new BrowserCloseTool();
    }
}
