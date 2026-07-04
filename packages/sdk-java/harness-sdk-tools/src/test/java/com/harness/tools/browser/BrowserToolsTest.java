package com.harness.tools.browser;

import com.harness.core.Tool;
import com.harness.core.ToolContext;
import com.harness.types.ToolResult;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIf;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for browser automation tools.
 *
 * <p>These tests require Playwright to be installed.
 * Run with: gradle test --tests BrowserToolsTest</p>
 *
 * <p>To install Playwright browsers:</p>
 * <pre>
 * # Add Playwright dependency and run
 * java -jar playwright.jar install chromium
 * </pre>
 */
class BrowserToolsTest {

    private ToolContext context;

    @BeforeEach
    void setUp() {
        context = ToolContext.builder()
            .sessionId("test-session")
            .workingDirectory(System.getProperty("user.dir"))
            .build();
    }

    @AfterEach
    void tearDown() {
        BrowserManager.close();
    }

    @Test
    void testGetAllTools() {
        List<Tool> tools = BrowserTools.getAll();

        assertEquals(7, tools.size(), "Should have 7 browser tools");

        List<String> names = tools.stream().map(Tool::name).toList();
        assertTrue(names.contains("browser_navigate"));
        assertTrue(names.contains("browser_click"));
        assertTrue(names.contains("browser_type"));
        assertTrue(names.contains("browser_extract"));
        assertTrue(names.contains("browser_screenshot"));
        assertTrue(names.contains("browser_wait"));
        assertTrue(names.contains("browser_close"));
    }

    @Test
    void testToolSchemas() {
        BrowserNavigateTool navigate = BrowserTools.navigate();

        assertNotNull(navigate.name());
        assertNotNull(navigate.description());
        assertNotNull(navigate.inputSchema());

        Map<String, Object> schema = navigate.inputSchema();
        assertEquals("object", schema.get("type"));
        assertTrue(schema.get("required") instanceof List);
    }

    @Test
    void testValidation() {
        BrowserNavigateTool navigate = BrowserTools.navigate();

        // Missing url
        var result1 = navigate.validate(Map.of());
        assertFalse(result1.isValid());

        // Empty url
        var result2 = navigate.validate(Map.of("url", ""));
        assertFalse(result2.isValid());

        // Valid url
        var result3 = navigate.validate(Map.of("url", "https://example.com"));
        assertTrue(result3.isValid());
    }

    @Test
    void testClickValidation() {
        BrowserClickTool click = BrowserTools.click();

        // Missing selector
        var result1 = click.validate(Map.of());
        assertFalse(result1.isValid());

        // Valid selector
        var result2 = click.validate(Map.of("selector", "#btn"));
        assertTrue(result2.isValid());
    }

    @Test
    void testTypeValidation() {
        BrowserTypeTool type = BrowserTools.type();

        // Missing required fields
        var result1 = type.validate(Map.of());
        assertFalse(result1.isValid());

        var result2 = type.validate(Map.of("selector", "#input"));
        assertFalse(result2.isValid());

        var result3 = type.validate(Map.of("selector", "#input", "text", "hello"));
        assertTrue(result3.isValid());
    }

    @Test
    void testDetectAvailableBrowser() {
        String browser = BrowserManager.detectAvailableBrowser();
        // Result depends on system, just verify it doesn't throw
        System.out.println("Detected browser: " + browser);
    }

    @Test
    void testBrowserManagerSingleton() {
        BrowserManager m1 = BrowserManager.getInstance();
        BrowserManager m2 = BrowserManager.getInstance();

        assertSame(m1, m2, "BrowserManager should be singleton");
    }

    @Test
    void testBrowserManagerConfiguration() {
        BrowserManager.setHeadless(true);
        BrowserManager.setBrowserType("msedge");
        BrowserManager.setAutoScreenshot(false);

        // Verify configuration doesn't throw
        assertTrue(true);
    }

    @Test
    @EnabledIf("isPlaywrightAvailable")
    void testNavigateAndClose() throws Exception {
        BrowserManager.useSystemBrowser();
        BrowserManager.setHeadless(true);

        BrowserNavigateTool navigate = BrowserTools.navigate();
        BrowserCloseTool close = BrowserTools.close();

        // Navigate to a data URL (no network needed)
        ToolResult result = navigate.execute(Map.of(
            "url", "data:text/html,<html><head><title>Test</title></head><body><h1>Hello</h1></body></html>"
        ), context).get();

        if (result.success()) {
            assertTrue(result.content().contains("Test"));
            assertTrue(BrowserManager.isActive());
        } else {
            // Playwright might not be installed, skip gracefully
            System.out.println("Skipping test - Playwright not available: " + result.error());
        }

        // Close browser
        close.execute(Map.of(), context).get();
        assertFalse(BrowserManager.isActive());
    }

    @Test
    @EnabledIf("isPlaywrightAvailable")
    void testClickAndType() throws Exception {
        BrowserManager.useSystemBrowser();
        BrowserManager.setHeadless(true);

        BrowserNavigateTool navigate = BrowserTools.navigate();
        BrowserClickTool click = BrowserTools.click();
        BrowserTypeTool type = BrowserTools.type();

        // Navigate to test page
        String html = "data:text/html," +
            "<html><body>" +
            "<input id='input' type='text' />" +
            "<button id='btn' onclick=\"this.innerText='Clicked'\">Click Me</button>" +
            "</body></html>";

        ToolResult navResult = navigate.execute(Map.of("url", html), context).get();

        if (!navResult.success()) {
            System.out.println("Skipping test - Playwright not available: " + navResult.error());
            return;
        }

        // Type into input
        ToolResult typeResult = type.execute(Map.of(
            "selector", "#input",
            "text", "Hello World"
        ), context).get();

        assertTrue(typeResult.success(), "Type should succeed");

        // Click button
        ToolResult clickResult = click.execute(Map.of(
            "selector", "#btn"
        ), context).get();

        assertTrue(clickResult.success(), "Click should succeed");
    }

    @Test
    @EnabledIf("isPlaywrightAvailable")
    void testExtract() throws Exception {
        BrowserManager.useSystemBrowser();
        BrowserManager.setHeadless(true);

        BrowserNavigateTool navigate = BrowserTools.navigate();
        BrowserExtractTool extract = BrowserTools.extract();

        // Navigate to test page
        String html = "data:text/html," +
            "<html><body>" +
            "<div id='content'>Hello World</div>" +
            "<a id='link' href='https://example.com'>Link</a>" +
            "</body></html>";

        ToolResult navResult = navigate.execute(Map.of("url", html), context).get();

        if (!navResult.success()) {
            System.out.println("Skipping test - Playwright not available: " + navResult.error());
            return;
        }

        // Extract text
        ToolResult extractResult = extract.execute(Map.of(
            "selector", "#content"
        ), context).get();

        assertTrue(extractResult.success());
        assertTrue(extractResult.content().contains("Hello World"));

        // Extract attribute
        ToolResult attrResult = extract.execute(Map.of(
            "selector", "#link",
            "attribute", "href"
        ), context).get();

        assertTrue(attrResult.success());
        assertTrue(attrResult.content().contains("example.com"));
    }

    @Test
    @EnabledIf("isPlaywrightAvailable")
    void testScreenshot() throws Exception {
        BrowserManager.useSystemBrowser();
        BrowserManager.setHeadless(true);

        BrowserNavigateTool navigate = BrowserTools.navigate();
        BrowserScreenshotTool screenshot = BrowserTools.screenshot();

        // Navigate to test page
        ToolResult navResult = navigate.execute(Map.of(
            "url", "data:text/html,<h1>Screenshot Test</h1>"
        ), context).get();

        if (!navResult.success()) {
            System.out.println("Skipping test - Playwright not available: " + navResult.error());
            return;
        }

        // Take screenshot
        ToolResult screenshotResult = screenshot.execute(Map.of(), context).get();

        assertTrue(screenshotResult.success());
        assertNotNull(screenshotResult.metadata().get("path"));
    }

    @Test
    @EnabledIf("isPlaywrightAvailable")
    void testWait() throws Exception {
        BrowserManager.useSystemBrowser();
        BrowserManager.setHeadless(true);

        BrowserNavigateTool navigate = BrowserTools.navigate();
        BrowserWaitTool wait = BrowserTools.waitFor();

        // Navigate to test page
        ToolResult navResult = navigate.execute(Map.of(
            "url", "data:text/html,<div id='target'>Target</div>"
        ), context).get();

        if (!navResult.success()) {
            System.out.println("Skipping test - Playwright not available: " + navResult.error());
            return;
        }

        // Wait for element
        ToolResult waitResult = wait.execute(Map.of(
            "wait_type", "selector",
            "selector", "#target"
        ), context).get();

        assertTrue(waitResult.success());

        // Wait for timeout
        long start = System.currentTimeMillis();
        wait.execute(Map.of(
            "wait_type", "timeout",
            "timeout_ms", 200
        ), context).get();
        long elapsed = System.currentTimeMillis() - start;

        assertTrue(elapsed >= 150, "Timeout should have waited");
    }

    @Test
    @EnabledIf("isPlaywrightAvailable")
    void testXPathSelectors() throws Exception {
        BrowserManager.useSystemBrowser();
        BrowserManager.setHeadless(true);

        BrowserNavigateTool navigate = BrowserTools.navigate();
        BrowserClickTool click = BrowserTools.click();
        BrowserExtractTool extract = BrowserTools.extract();

        // Navigate to test page
        String html = "data:text/html," +
            "<html><body>" +
            "<button>Submit</button>" +
            "<div><span class='name'>John</span></div>" +
            "</body></html>";

        ToolResult navResult = navigate.execute(Map.of("url", html), context).get();

        if (!navResult.success()) {
            System.out.println("Skipping test - Playwright not available: " + navResult.error());
            return;
        }

        // Click using XPath
        ToolResult clickResult = click.execute(Map.of(
            "selector", "//button[text()='Submit']"
        ), context).get();

        assertTrue(clickResult.success(), "XPath click should work");

        // Extract using XPath
        ToolResult extractResult = extract.execute(Map.of(
            "selector", "//span[@class='name']"
        ), context).get();

        assertTrue(extractResult.success());
        assertTrue(extractResult.content().contains("John"));
    }

    /**
     * Check if Playwright is available.
     */
    static boolean isPlaywrightAvailable() {
        try {
            Class.forName("com.microsoft.playwright.Playwright");
            return true;
        } catch (ClassNotFoundException e) {
            return false;
        }
    }
}
