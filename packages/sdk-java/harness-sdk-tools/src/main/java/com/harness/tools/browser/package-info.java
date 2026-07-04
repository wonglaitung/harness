/**
 * Browser automation tools using Playwright.
 *
 * <p>Provides deterministic browser automation for scenarios requiring
 * precise control (e.g., financial/banking operations).</p>
 *
 * <h2>Design Principles</h2>
 * <ul>
 *   <li><strong>Atomic operations:</strong> Each tool performs one action</li>
 *   <li><strong>Automatic waiting:</strong> Wait for elements before interaction</li>
 *   <li><strong>Screenshot audit:</strong> Optional screenshots for each operation</li>
 *   <li><strong>Error recovery:</strong> Retry on transient failures</li>
 * </ul>
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
 * <h2>Usage Example</h2>
 * <pre>{@code
 * // Configure for intranet (use system Edge)
 * BrowserManager.useSystemBrowser();
 *
 * // Create agent with browser tools
 * List<Tool> tools = BrowserTools.getAll();
 * AgentHarness agent = AgentHarness.builder()
 *     .model("claude-sonnet-4-6")
 *     .tools(tools)
 *     .build();
 *
 * // Execute browser automation
 * agent.run("Navigate to https://example.com and click the login button");
 * }</pre>
 */
package com.harness.tools.browser;
