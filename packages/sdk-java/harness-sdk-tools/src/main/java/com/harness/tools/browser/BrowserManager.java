package com.harness.tools.browser;

import com.microsoft.playwright.Browser;
import com.microsoft.playwright.BrowserType;
import com.microsoft.playwright.Page;
import com.microsoft.playwright.Playwright;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Locale;

/**
 * Singleton manager for Playwright browser instances.
 *
 * <p>Ensures a single browser instance is shared across all browser tools,
 * with proper lifecycle management and error recovery.</p>
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
 * // Configure to use system Edge (intranet-friendly)
 * BrowserManager.useSystemBrowser();
 *
 * // Get page for automation
 * Page page = BrowserManager.getPage();
 *
 * // Close when done
 * BrowserManager.close();
 * }</pre>
 */
public class BrowserManager {

    private static final Logger logger = LoggerFactory.getLogger(BrowserManager.class);

    private static BrowserManager instance;
    private Playwright playwright;
    private Browser browser;
    private Page page;
    private Path screenshotDir;
    private int stepCounter = 0;

    // Configuration
    private boolean headless = false;
    private String browserType = "chromium";
    private int defaultTimeout = 30000;
    private boolean autoScreenshot = true;

    private BrowserManager() {
        // Singleton
    }

    /**
     * Get the singleton instance.
     */
    public static synchronized BrowserManager getInstance() {
        if (instance == null) {
            instance = new BrowserManager();
        }
        return instance;
    }

    /**
     * Get or create a browser page.
     *
     * @return Playwright Page instance
     * @throws IllegalStateException if Playwright is not available
     */
    public static Page getPage() {
        return getInstance().getOrCreatePage();
    }

    /**
     * Close the browser and cleanup resources.
     */
    public static void close() {
        getInstance().closeInternal();
    }

    /**
     * Check if browser is active.
     */
    public static boolean isActive() {
        return getInstance().page != null && !getInstance().page.isClosed();
    }

    /**
     * Configure browser settings.
     */
    public static void configure(boolean headless, String browserType, int defaultTimeout, boolean autoScreenshot) {
        BrowserManager manager = getInstance();
        manager.headless = headless;
        manager.browserType = browserType;
        manager.defaultTimeout = defaultTimeout;
        manager.autoScreenshot = autoScreenshot;
    }

    /**
     * Configure to use headless mode.
     */
    public static void setHeadless(boolean headless) {
        getInstance().headless = headless;
    }

    /**
     * Configure browser type.
     *
     * @param browserType chromium, firefox, webkit, msedge, or chrome
     */
    public static void setBrowserType(String browserType) {
        getInstance().browserType = browserType;
    }

    /**
     * Check if auto-screenshot is enabled.
     */
    public boolean isAutoScreenshot() {
        return autoScreenshot;
    }

    /**
     * Enable or disable auto-screenshot.
     */
    public static void setAutoScreenshot(boolean autoScreenshot) {
        getInstance().autoScreenshot = autoScreenshot;
    }

    /**
     * Detect available browser on the system.
     *
     * <p>Detection order (for intranet/offline scenarios):</p>
     * <ol>
     *   <li>Microsoft Edge (Windows enterprise standard)</li>
     *   <li>Google Chrome</li>
     *   <li>Playwright's bundled Chromium (if installed)</li>
     * </ol>
     *
     * @return Browser type string or null if no browser found
     */
    public static String detectAvailableBrowser() {
        String os = System.getProperty("os.name", "").toLowerCase(Locale.ROOT);

        if (os.contains("win")) {
            // Check for Edge (Windows 10/11 enterprise standard)
            String[] edgePaths = {
                "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
                "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"
            };
            for (String path : edgePaths) {
                if (Files.exists(Path.of(path))) {
                    logger.info("Detected: Microsoft Edge");
                    return "msedge";
                }
            }

            // Check for Chrome
            String[] chromePaths = {
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
            };
            for (String path : chromePaths) {
                if (Files.exists(Path.of(path))) {
                    logger.info("Detected: Google Chrome");
                    return "chrome";
                }
            }
        } else if (os.contains("mac")) {
            // macOS
            Path edgePath = Path.of("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge");
            Path chromePath = Path.of("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome");

            if (Files.exists(edgePath)) {
                return "msedge";
            }
            if (Files.exists(chromePath)) {
                return "chrome";
            }
        } else if (os.contains("nix") || os.contains("nux")) {
            // Linux - check PATH
            // For simplicity, just check common paths
            if (Files.exists(Path.of("/usr/bin/microsoft-edge")) || Files.exists(Path.of("/usr/bin/msedge"))) {
                return "msedge";
            }
            if (Files.exists(Path.of("/usr/bin/google-chrome")) || Files.exists(Path.of("/usr/bin/chrome"))) {
                return "chrome";
            }
        }

        // Check if Playwright's bundled browser is installed
        String home = System.getProperty("user.home");
        Path playwrightCache = Path.of(home, ".cache", "ms-playwright");
        if (Files.exists(playwrightCache)) {
            try {
                Files.list(playwrightCache)
                    .filter(p -> p.getFileName().toString().startsWith("chromium-"))
                    .findFirst()
                    .ifPresent(p -> {
                        logger.info("Detected: Playwright bundled Chromium");
                    });
                if (Files.list(playwrightCache).anyMatch(p -> p.getFileName().toString().startsWith("chromium-"))) {
                    return "chromium";
                }
            } catch (Exception e) {
                logger.debug("Failed to list playwright cache: {}", e.getMessage());
            }
        }

        return null;
    }

    /**
     * Configure to use system browser (Edge/Chrome).
     *
     * <p>Automatically detects and configures the best available browser.
     * Ideal for intranet/offline environments.</p>
     *
     * @return true if a system browser was found and configured
     */
    public static boolean useSystemBrowser() {
        String browser = detectAvailableBrowser();
        if (browser != null && (browser.equals("msedge") || browser.equals("chrome"))) {
            getInstance().browserType = browser;
            logger.info("Configured to use system browser: {}", browser);
            return true;
        }
        return false;
    }

    /**
     * Take a screenshot of the current page.
     *
     * @param name Optional name for the screenshot file
     * @return Path to the screenshot file, or null if no page
     */
    public static String takeScreenshot(String name) {
        return getInstance().takeScreenshotInternal(name);
    }

    /**
     * Get current page URL.
     */
    public static String getCurrentUrl() {
        Page p = getInstance().page;
        return p != null ? p.url() : null;
    }

    /**
     * Get current page title.
     */
    public static String getCurrentTitle() {
        Page p = getInstance().page;
        if (p != null) {
            try {
                return p.title();
            } catch (Exception e) {
                return null;
            }
        }
        return null;
    }

    // === Internal methods ===

    private Page getOrCreatePage() {
        if (page == null || page.isClosed()) {
            startBrowser();
        }
        return page;
    }

    private void startBrowser() {
        logger.info("Starting {} browser (headless={})", browserType, headless);

        playwright = Playwright.create();

        BrowserType.LaunchOptions options = new BrowserType.LaunchOptions()
            .setHeadless(headless);

        switch (browserType.toLowerCase()) {
            case "firefox":
                browser = playwright.firefox().launch(options);
                break;
            case "webkit":
                browser = playwright.webkit().launch(options);
                break;
            case "msedge":
                browser = playwright.chromium().launch(options.setChannel("msedge"));
                break;
            case "chrome":
                browser = playwright.chromium().launch(options.setChannel("chrome"));
                break;
            default:
                browser = playwright.chromium().launch(options);
                break;
        }

        page = browser.newPage();
        page.setDefaultTimeout(defaultTimeout);

        // Create screenshot directory
        try {
            screenshotDir = Files.createTempDirectory("browser_");
        } catch (Exception e) {
            screenshotDir = Path.of(System.getProperty("java.io.tmpdir"), "browser_" + System.currentTimeMillis());
        }
        stepCounter = 0;

        logger.info("Browser started, screenshots saved to: {}", screenshotDir);
    }

    private void closeInternal() {
        if (browser != null) {
            browser.close();
            browser = null;
        }
        if (playwright != null) {
            playwright.close();
            playwright = null;
        }
        page = null;
        screenshotDir = null;
        stepCounter = 0;

        logger.info("Browser closed");
    }

    private String takeScreenshotInternal(String name) {
        if (page == null || page.isClosed()) {
            return null;
        }

        stepCounter++;
        if (name == null) {
            name = String.format("step_%03d", stepCounter);
        }

        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("HHmmss"));
        String filename = name + "_" + timestamp + ".png";

        if (screenshotDir == null) {
            try {
                screenshotDir = Files.createTempDirectory("browser_");
            } catch (Exception e) {
                screenshotDir = Path.of(System.getProperty("java.io.tmpdir"));
            }
        }

        Path screenshotPath = screenshotDir.resolve(filename);
        page.screenshot(new Page.ScreenshotOptions().setPath(screenshotPath));

        logger.debug("Screenshot saved: {}", screenshotPath);
        return screenshotPath.toString();
    }
}
