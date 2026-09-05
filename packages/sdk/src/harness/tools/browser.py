"""
Browser automation tools using Playwright.

Provides deterministic browser automation for scenarios requiring
precise control (e.g., financial/banking operations).

Design principles:
- Atomic operations: Each tool performs one action
- Automatic waiting: Wait for elements before interaction
- Screenshot audit: Optional screenshots for each operation
- Error recovery: Retry on transient failures
"""

from __future__ import annotations

import base64
import logging
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from harness.tools.base import Tool, ToolContext
from harness.types import ToolResult

logger = logging.getLogger(__name__)

# Try to import playwright
try:
    from playwright.async_api import async_playwright
    from playwright.async_api._generated import Browser, Page, Playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    Browser = None
    Page = None
    Playwright = None


class BrowserManager:
    """
    Singleton manager for Playwright browser instances.

    Ensures a single browser instance is shared across all browser tools,
    with proper lifecycle management and error recovery.

    Usage:
        page = await BrowserManager.get_page()
        await BrowserManager.close()
    """

    _instance: BrowserManager | None = None
    _playwright: Playwright | None = None
    _browser: Browser | None = None
    _page: Page | None = None
    _screenshot_dir: Path | None = None
    _step_counter: int = 0

    # Configuration
    headless: bool = False
    browser_type: str = "chromium"
    # Supported browser types:
    # - "chromium": Playwright's bundled Chromium (requires `playwright install`)
    # - "firefox": Playwright's bundled Firefox (requires `playwright install`)
    # - "webkit": Playwright's bundled WebKit (requires `playwright install`)
    # - "msedge": System Microsoft Edge (no download needed, ideal for intranet)
    # - "chrome": System Google Chrome (no download needed)
    default_timeout: int = 30000  # ms
    auto_screenshot: bool = True

    def __new__(cls) -> BrowserManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def get_page(cls) -> Page:
        """
        Get or create a browser page.

        Returns:
            Playwright Page instance

        Raises:
            RuntimeError: If Playwright is not installed
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError(
                "Playwright is not installed. "
                "Install with: pip install playwright && playwright install"
            )

        if cls._page is None or cls._page.is_closed():
            await cls._start_browser()

        return cls._page

    @classmethod
    async def _start_browser(cls) -> None:
        """
        Start a new browser instance.

        Browser types:
        - "chromium": Playwright's bundled Chromium (requires `playwright install`)
        - "firefox": Playwright's bundled Firefox (requires `playwright install`)
        - "webkit": Playwright's bundled WebKit (requires `playwright install`)
        - "msedge": System Microsoft Edge (no download needed, ideal for intranet)
        - "chrome": System Google Chrome (no download needed)
        """
        logger.info(f"Starting {cls.browser_type} browser (headless={cls.headless})")

        cls._playwright = await async_playwright().start()

        # Select browser type
        if cls.browser_type == "firefox":
            cls._browser = await cls._playwright.firefox.launch(headless=cls.headless)
        elif cls.browser_type == "webkit":
            cls._browser = await cls._playwright.webkit.launch(headless=cls.headless)
        elif cls.browser_type == "msedge":
            # Use system Microsoft Edge (no download needed)
            cls._browser = await cls._playwright.chromium.launch(
                channel="msedge",
                headless=cls.headless,
            )
        elif cls.browser_type == "chrome":
            # Use system Google Chrome (no download needed)
            cls._browser = await cls._playwright.chromium.launch(
                channel="chrome",
                headless=cls.headless,
            )
        else:
            # Default: Playwright's bundled Chromium
            cls._browser = await cls._playwright.chromium.launch(headless=cls.headless)

        cls._page = await cls._browser.new_page()
        cls._page.set_default_timeout(cls.default_timeout)

        # Create screenshot directory
        cls._screenshot_dir = Path(tempfile.mkdtemp(prefix="browser_"))
        cls._step_counter = 0

        logger.info(f"Browser started, screenshots saved to: {cls._screenshot_dir}")

    @classmethod
    async def close(cls) -> None:
        """Close the browser and cleanup resources."""
        if cls._browser:
            await cls._browser.close()
            cls._browser = None

        if cls._playwright:
            await cls._playwright.stop()
            cls._playwright = None

        cls._page = None
        cls._screenshot_dir = None
        cls._step_counter = 0

        logger.info("Browser closed")

    @classmethod
    async def take_screenshot(cls, name: str | None = None) -> str | None:
        """
        Take a screenshot of the current page.

        Args:
            name: Optional name for the screenshot file

        Returns:
            Path to the screenshot file, or None if no page
        """
        if cls._page is None or cls._page.is_closed():
            return None

        cls._step_counter += 1

        if name is None:
            name = f"step_{cls._step_counter:03d}"

        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{name}_{timestamp}.png"

        if cls._screenshot_dir is None:
            cls._screenshot_dir = Path(tempfile.mkdtemp(prefix="browser_"))

        screenshot_path = cls._screenshot_dir / filename

        await cls._page.screenshot(path=str(screenshot_path))
        logger.debug(f"Screenshot saved: {screenshot_path}")

        return str(screenshot_path)

    @classmethod
    def get_current_url(cls) -> str | None:
        """Get the current page URL."""
        if cls._page is None:
            return None
        return cls._page.url

    @classmethod
    def get_current_title(cls) -> str | None:
        """Get the current page title."""
        if cls._page is None:
            return None
        try:
            return cls._page.title()
        except Exception:
            return None

    @classmethod
    def is_active(cls) -> bool:
        """Check if browser is active."""
        return cls._page is not None and not cls._page.is_closed()

    @classmethod
    def detect_available_browser(cls) -> str | None:
        """
        Detect available browser on the system.

        Returns:
            Browser type string or None if no browser found

        Detection order (for intranet/offline scenarios):
        1. Microsoft Edge (Windows enterprise standard)
        2. Google Chrome
        3. Playwright's bundled Chromium (if installed)
        """
        import platform
        import shutil

        system = platform.system()

        if system == "Windows":
            # Check for Edge (Windows 10/11 enterprise standard)
            edge_paths = [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            ]
            for path in edge_paths:
                if Path(path).exists():
                    logger.info("Detected: Microsoft Edge")
                    return "msedge"

            # Check for Chrome
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ]
            for path in chrome_paths:
                if Path(path).exists():
                    logger.info("Detected: Google Chrome")
                    return "chrome"

        elif system == "Darwin":  # macOS
            edge_path = "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
            chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

            if Path(edge_path).exists():
                return "msedge"
            if Path(chrome_path).exists():
                return "chrome"

        elif system == "Linux":
            # Check for Edge/Chrome in common paths
            if shutil.which("microsoft-edge") or shutil.which("msedge"):
                return "msedge"
            if shutil.which("google-chrome") or shutil.which("chrome"):
                return "chrome"

        # Check if Playwright's bundled browser is installed
        playwright_cache = Path.home() / ".cache" / "ms-playwright"
        if playwright_cache.exists():
            chromium_dirs = list(playwright_cache.glob("chromium-*"))
            if chromium_dirs:
                logger.info("Detected: Playwright bundled Chromium")
                return "chromium"

        return None

    @classmethod
    def use_system_browser(cls) -> bool:
        """
        Configure to use system browser (Edge/Chrome).

        Automatically detects and configures the best available browser.
        Ideal for intranet/offline environments.

        Returns:
            True if a system browser was found and configured
        """
        browser = cls.detect_available_browser()
        if browser and browser in ("msedge", "chrome"):
            cls.browser_type = browser
            logger.info(f"Configured to use system browser: {browser}")
            return True
        return False

    @classmethod
    def configure(
        cls,
        headless: bool | None = None,
        browser_type: str | None = None,
        default_timeout: int | None = None,
        auto_screenshot: bool | None = None,
    ) -> None:
        """
        Configure browser settings.

        Args:
            headless: Run in headless mode
            browser_type: Browser type (chromium, firefox, webkit)
            default_timeout: Default timeout in milliseconds
            auto_screenshot: Auto-screenshot after each action
        """
        if headless is not None:
            cls.headless = headless
        if browser_type is not None:
            cls.browser_type = browser_type
        if default_timeout is not None:
            cls.default_timeout = default_timeout
        if auto_screenshot is not None:
            cls.auto_screenshot = auto_screenshot


class BrowserNavigateTool(Tool):
    """
    Navigate to a URL.

    Waits for the page to load before returning.
    """

    @property
    def name(self) -> str:
        return "browser_navigate"

    @property
    def description(self) -> str:
        return "Navigate to a URL and wait for the page to load."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to navigate to (e.g., 'https://example.com')",
                },
                "wait_until": {
                    "type": "string",
                    "enum": ["load", "domcontentloaded", "networkidle"],
                    "description": (
                        "Wait condition: 'load' (default), 'domcontentloaded', or 'networkidle'"
                    ),
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in milliseconds (default: 30000)",
                },
            },
            "required": ["url"],
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        if not PLAYWRIGHT_AVAILABLE:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=(
                    "Playwright is not installed. "
                    "Install with: pip install playwright && playwright install"
                ),
            )

        url = arguments["url"]
        wait_until = arguments.get("wait_until", "load")
        timeout = arguments.get("timeout", 30000)

        try:
            page = await BrowserManager.get_page()
            start_time = time.time()

            await page.goto(url, wait_until=wait_until, timeout=timeout)

            elapsed = time.time() - start_time
            title = await page.title()

            result_content = f"""✅ Navigate: {url}
Title: {title}
Wait: {wait_until}
Time: {elapsed:.2f}s"""

            # Auto screenshot
            screenshot_path = None
            if BrowserManager.auto_screenshot:
                screenshot_path = await BrowserManager.take_screenshot("navigate")
                if screenshot_path:
                    result_content += f"\nScreenshot: {screenshot_path}"

            return ToolResult(
                tool_call_id="",
                success=True,
                content=result_content,
                metadata={
                    "url": url,
                    "title": title,
                    "elapsed_seconds": elapsed,
                    "screenshot_path": screenshot_path,
                },
            )

        except Exception as e:
            logger.exception(f"Navigate failed: {e}")
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Navigate failed: {str(e)}",
            )


class BrowserClickTool(Tool):
    """
    Click an element on the page.

    Waits for the element to be visible and clickable before clicking.
    Retries on transient failures.
    """

    @property
    def name(self) -> str:
        return "browser_click"

    @property
    def description(self) -> str:
        return "Click an element on the page. Waits for element to be visible and clickable."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": (
                        "CSS selector or XPath (e.g., '#submit-btn', '//button[text()=\"Submit\"]')"
                    ),
                },
                "timeout": {
                    "type": "integer",
                    "description": "Wait timeout in milliseconds (default: 10000)",
                },
                "force": {
                    "type": "boolean",
                    "description": "Force click even if element is not visible (default: false)",
                },
                "retry_count": {
                    "type": "integer",
                    "description": "Number of retries on failure (default: 2)",
                },
                "first": {
                    "type": "boolean",
                    "description": (
                        "Click the first matching element when selector matches multiple "
                        "(default: true, avoids 'strict mode violation' errors)"
                    ),
                },
            },
            "required": ["selector"],
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        if not PLAYWRIGHT_AVAILABLE:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error="Playwright is not installed.",
            )

        selector = arguments["selector"]
        timeout = arguments.get("timeout", 10000)
        force = arguments.get("force", False)
        retry_count = arguments.get("retry_count", 2)
        use_first = arguments.get("first", True)  # Default to first to avoid strict mode violation

        try:
            page = await BrowserManager.get_page()
            start_time = time.time()

            # Determine if XPath
            is_xpath = selector.startswith("//") or selector.startswith("(//")

            last_error = None
            for attempt in range(retry_count + 1):
                try:
                    if is_xpath:
                        element = page.locator(f"xpath={selector}")
                    else:
                        element = page.locator(selector)

                    # Use .first to avoid strict mode violation when multiple elements match
                    if use_first:
                        element = element.first

                    # Wait for element to be visible
                    if not force:
                        await element.wait_for(state="visible", timeout=timeout)

                    await element.click(force=force)

                    elapsed = time.time() - start_time

                    result_content = f"""✅ Click: {selector}
Attempts: {attempt + 1}
Time: {elapsed * 1000:.0f}ms"""

                    # Auto screenshot
                    screenshot_path = None
                    if BrowserManager.auto_screenshot:
                        screenshot_path = await BrowserManager.take_screenshot("click")
                        if screenshot_path:
                            result_content += f"\nScreenshot: {screenshot_path}"

                    return ToolResult(
                        tool_call_id="",
                        success=True,
                        content=result_content,
                        metadata={
                            "selector": selector,
                            "elapsed_ms": elapsed * 1000,
                            "attempts": attempt + 1,
                            "screenshot_path": screenshot_path,
                        },
                    )

                except Exception as e:
                    last_error = e
                    if attempt < retry_count:
                        logger.warning(f"Click attempt {attempt + 1} failed, retrying: {e}")
                        await page.wait_for_timeout(500)

            raise last_error if last_error else Exception("Click failed")

        except Exception as e:
            logger.exception(f"Click failed: {e}")
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Click failed: {str(e)}",
            )


class BrowserTypeTool(Tool):
    """
    Type text into an input field.

    Waits for the element to be visible, optionally clears existing text first.
    """

    @property
    def name(self) -> str:
        return "browser_type"

    @property
    def description(self) -> str:
        return "Type text into an input field. Waits for element to be visible."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector or XPath for the input field",
                },
                "text": {
                    "type": "string",
                    "description": "Text to type",
                },
                "clear_first": {
                    "type": "boolean",
                    "description": "Clear existing text before typing (default: true)",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Wait timeout in milliseconds (default: 10000)",
                },
                "delay": {
                    "type": "integer",
                    "description": "Delay between keystrokes in milliseconds (default: 50)",
                },
                "press_enter": {
                    "type": "boolean",
                    "description": "Press Enter after typing to submit form (default: false)",
                },
            },
            "required": ["selector", "text"],
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        if not PLAYWRIGHT_AVAILABLE:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error="Playwright is not installed.",
            )

        selector = arguments["selector"]
        text = arguments["text"]
        clear_first = arguments.get("clear_first", True)
        timeout = arguments.get("timeout", 10000)
        delay = arguments.get("delay", 50)
        press_enter = arguments.get("press_enter", False)

        try:
            page = await BrowserManager.get_page()
            start_time = time.time()

            # Determine if XPath
            is_xpath = selector.startswith("//") or selector.startswith("(//")

            element = page.locator(f"xpath={selector}") if is_xpath else page.locator(selector)

            # Wait for element to be visible
            await element.wait_for(state="visible", timeout=timeout)

            # Clear existing text if requested
            if clear_first:
                await element.fill("")
                logger.debug("Cleared existing text")

            # Type with realistic delay
            await element.type(text, delay=delay)

            # Press Enter if requested (useful for form submission)
            if press_enter:
                await page.keyboard.press("Enter")
                logger.debug("Pressed Enter")

            elapsed = time.time() - start_time

            result_content = f"""✅ Type: {selector}
Text: {text[:50]}{"..." if len(text) > 50 else ""}
Length: {len(text)}
Time: {elapsed * 1000:.0f}ms"""
            if press_enter:
                result_content += "\nEnter: pressed"

            # Auto screenshot
            screenshot_path = None
            if BrowserManager.auto_screenshot:
                screenshot_path = await BrowserManager.take_screenshot("type")
                if screenshot_path:
                    result_content += f"\nScreenshot: {screenshot_path}"

            return ToolResult(
                tool_call_id="",
                success=True,
                content=result_content,
                metadata={
                    "selector": selector,
                    "text_length": len(text),
                    "elapsed_ms": elapsed * 1000,
                    "press_enter": press_enter,
                    "screenshot_path": screenshot_path,
                },
            )

        except Exception as e:
            logger.exception(f"Type failed: {e}")
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Type failed: {str(e)}",
            )


class BrowserExtractTool(Tool):
    """
    Extract data from the page.

    Can extract text content, attributes, or structured data from elements.
    """

    @property
    def name(self) -> str:
        return "browser_extract"

    @property
    def description(self) -> str:
        return "Extract text or data from page elements."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": (
                        "CSS selector or XPath for elements to extract "
                        "(optional, extracts from body if not specified)"
                    ),
                },
                "attribute": {
                    "type": "string",
                    "description": (
                        "Attribute to extract (e.g., 'href', 'src'). "
                        "Extracts text content if not specified."
                    ),
                },
                "multiple": {
                    "type": "boolean",
                    "description": (
                        "Extract all matching elements (default: false, extract first only)"
                    ),
                },
                "as_markdown": {
                    "type": "boolean",
                    "description": "Convert extracted content to Markdown (default: false)",
                },
            },
            "required": [],
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        if not PLAYWRIGHT_AVAILABLE:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error="Playwright is not installed.",
            )

        selector = arguments.get("selector", "body")
        attribute = arguments.get("attribute")
        multiple = arguments.get("multiple", False)
        as_markdown = arguments.get("as_markdown", False)

        try:
            page = await BrowserManager.get_page()

            # Determine if XPath
            is_xpath = selector.startswith("//") or selector.startswith("(")

            locator = page.locator(f"xpath={selector}") if is_xpath else page.locator(selector)

            results = []

            if multiple:
                count = await locator.count()
                for i in range(count):
                    element = locator.nth(i)
                    if attribute:
                        value = await element.get_attribute(attribute)
                    elif as_markdown:
                        # Use inner text for better formatting
                        value = await element.inner_text()
                    else:
                        value = await element.text_content()
                    if value:
                        results.append(value.strip())
            else:
                if attribute:
                    value = await locator.get_attribute(attribute)
                elif as_markdown:
                    value = await locator.inner_text()
                else:
                    value = await locator.text_content()
                if value:
                    results.append(value.strip())

            if not results:
                return ToolResult(
                    tool_call_id="",
                    success=True,
                    content="No content extracted (element may be empty or not found)",
                )

            content = "\n---\n".join(results) if len(results) > 1 else results[0]

            return ToolResult(
                tool_call_id="",
                success=True,
                content=content,
                metadata={
                    "selector": selector,
                    "attribute": attribute,
                    "count": len(results),
                    "multiple": multiple,
                },
            )

        except Exception as e:
            logger.exception(f"Extract failed: {e}")
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Extract failed: {str(e)}",
            )


class BrowserScreenshotTool(Tool):
    """
    Take a screenshot of the page or a specific element.

    Returns the path to the screenshot file and optionally base64 encoded image.
    """

    @property
    def name(self) -> str:
        return "browser_screenshot"

    @property
    def description(self) -> str:
        return "Take a screenshot of the current page or a specific element."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": (
                        "CSS selector or XPath for a specific element "
                        "(optional, full page if not specified)"
                    ),
                },
                "full_page": {
                    "type": "boolean",
                    "description": "Capture full scrollable page (default: false)",
                },
                "return_base64": {
                    "type": "boolean",
                    "description": "Return base64 encoded image in metadata (default: false)",
                },
            },
            "required": [],
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        if not PLAYWRIGHT_AVAILABLE:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error="Playwright is not installed.",
            )

        selector = arguments.get("selector")
        full_page = arguments.get("full_page", False)
        return_base64 = arguments.get("return_base64", False)

        try:
            page = await BrowserManager.get_page()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"

            if BrowserManager._screenshot_dir is None:
                BrowserManager._screenshot_dir = Path(tempfile.mkdtemp(prefix="browser_"))

            screenshot_path = BrowserManager._screenshot_dir / filename

            screenshot_bytes: bytes | None = None

            if selector:
                # Screenshot specific element
                is_xpath = selector.startswith("//") or selector.startswith("(")
                locator = page.locator(f"xpath={selector}") if is_xpath else page.locator(selector)

                screenshot_bytes = await locator.screenshot(path=str(screenshot_path))
            else:
                # Screenshot full page or viewport
                screenshot_bytes = await page.screenshot(
                    path=str(screenshot_path),
                    full_page=full_page,
                )

            result_content = f"""✅ Screenshot captured
Path: {screenshot_path}
Full page: {full_page}
Size: {len(screenshot_bytes) if screenshot_bytes else 0} bytes"""

            metadata = {
                "path": str(screenshot_path),
                "full_page": full_page,
                "size_bytes": len(screenshot_bytes) if screenshot_bytes else 0,
            }

            if return_base64 and screenshot_bytes:
                metadata["base64"] = base64.b64encode(screenshot_bytes).decode("utf-8")

            return ToolResult(
                tool_call_id="",
                success=True,
                content=result_content,
                metadata=metadata,
            )

        except Exception as e:
            logger.exception(f"Screenshot failed: {e}")
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Screenshot failed: {str(e)}",
            )


class BrowserCloseTool(Tool):
    """
    Close the browser instance.

    Use this to cleanup resources when done with browser automation.
    """

    @property
    def name(self) -> str:
        return "browser_close"

    @property
    def description(self) -> str:
        return "Close the browser instance and cleanup resources."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        if not PLAYWRIGHT_AVAILABLE:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error="Playwright is not installed.",
            )

        try:
            await BrowserManager.close()
            return ToolResult(
                tool_call_id="",
                success=True,
                content="✅ Browser closed",
            )

        except Exception as e:
            logger.exception(f"Close failed: {e}")
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Close failed: {str(e)}",
            )


class BrowserWaitTool(Tool):
    """
    Wait for a condition on the page.

    Can wait for:
    - Element to appear/disappear
    - URL to change
    - A timeout
    """

    @property
    def name(self) -> str:
        return "browser_wait"

    @property
    def description(self) -> str:
        return "Wait for a condition on the page (element, URL, or timeout)."

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "wait_type": {
                    "type": "string",
                    "enum": ["selector", "url", "timeout"],
                    "description": "What to wait for: 'selector' (element), 'url', or 'timeout'",
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector or XPath (required if wait_type='selector')",
                },
                "state": {
                    "type": "string",
                    "enum": ["visible", "hidden", "attached", "detached"],
                    "description": "Element state to wait for (default: 'visible')",
                },
                "url_pattern": {
                    "type": "string",
                    "description": "URL pattern to wait for (required if wait_type='url')",
                },
                "timeout_ms": {
                    "type": "integer",
                    "description": "Timeout in milliseconds (default: 30000)",
                },
            },
            "required": ["wait_type"],
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        if not PLAYWRIGHT_AVAILABLE:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error="Playwright is not installed.",
            )

        wait_type = arguments["wait_type"]
        timeout_ms = arguments.get("timeout_ms", 30000)

        try:
            page = await BrowserManager.get_page()
            start_time = time.time()

            if wait_type == "selector":
                selector = arguments.get("selector")
                if not selector:
                    return ToolResult(
                        tool_call_id="",
                        success=False,
                        content="",
                        error="selector is required for wait_type='selector'",
                    )

                state = arguments.get("state", "visible")

                is_xpath = selector.startswith("//") or selector.startswith("(")
                locator = page.locator(f"xpath={selector}") if is_xpath else page.locator(selector)

                await locator.wait_for(state=state, timeout=timeout_ms)
                elapsed = time.time() - start_time

                return ToolResult(
                    tool_call_id="",
                    success=True,
                    content=f"✅ Wait: {selector} became {state} in {elapsed * 1000:.0f}ms",
                    metadata={
                        "wait_type": wait_type,
                        "selector": selector,
                        "state": state,
                        "elapsed_ms": elapsed * 1000,
                    },
                )

            elif wait_type == "url":
                url_pattern = arguments.get("url_pattern", "**")
                await page.wait_for_url(url_pattern, timeout=timeout_ms)
                elapsed = time.time() - start_time

                return ToolResult(
                    tool_call_id="",
                    success=True,
                    content=(
                        f"✅ Wait: URL matched '{url_pattern}' in {elapsed * 1000:.0f}ms\n"
                        f"Current URL: {page.url}"
                    ),
                    metadata={
                        "wait_type": wait_type,
                        "url_pattern": url_pattern,
                        "current_url": page.url,
                        "elapsed_ms": elapsed * 1000,
                    },
                )

            elif wait_type == "timeout":
                timeout_value = arguments.get("timeout_ms", 1000)
                await page.wait_for_timeout(timeout_value)
                elapsed = time.time() - start_time

                return ToolResult(
                    tool_call_id="",
                    success=True,
                    content=f"✅ Wait: {timeout_value}ms timeout completed",
                    metadata={
                        "wait_type": wait_type,
                        "timeout_ms": timeout_value,
                        "elapsed_ms": elapsed * 1000,
                    },
                )

            else:
                return ToolResult(
                    tool_call_id="",
                    success=False,
                    content="",
                    error=f"Unknown wait_type: {wait_type}",
                )

        except Exception as e:
            logger.exception(f"Wait failed: {e}")
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Wait failed: {str(e)}",
            )


# Convenience function to get all browser tools
def get_browser_tools() -> list[Tool]:
    """
    Get all browser automation tools.

    Returns:
        List of browser Tool instances
    """
    return [
        BrowserNavigateTool(),
        BrowserClickTool(),
        BrowserTypeTool(),
        BrowserExtractTool(),
        BrowserScreenshotTool(),
        BrowserWaitTool(),
        BrowserCloseTool(),
    ]
