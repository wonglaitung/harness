"""
Browser controller - manages browser lifecycle and tools.

Provides browser automation control for the client, allowing users
to start/stop browser instances and inject browser tools into AgentHarness.
"""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Check if playwright is available
try:
    from harness.tools.browser import BrowserManager, get_browser_tools, PLAYWRIGHT_AVAILABLE
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    BrowserManager = None
    get_browser_tools = None


@dataclass
class BrowserConfig:
    """Browser configuration."""

    browser_type: str = "msedge"  # msedge, chrome, chromium, firefox, webkit
    headless: bool = False  # Show browser window by default
    default_timeout: int = 30000  # milliseconds
    auto_screenshot: bool = True  # Auto-screenshot for audit


class BrowserController:
    """
    Controller for managing browser automation.

    Features:
    - Start/stop browser instances
    - Configure browser settings
    - Provide browser tools for AgentHarness
    - Track browser state
    """

    def __init__(self):
        self._config = BrowserConfig()
        self._active = False
        self._tools: list = []

    def configure(self, config: BrowserConfig):
        """Update browser configuration."""
        self._config = config
        logger.info(f"Browser config updated: type={config.browser_type}, headless={config.headless}")

    def is_available(self) -> bool:
        """Check if playwright is available."""
        return PLAYWRIGHT_AVAILABLE

    def is_active(self) -> bool:
        """Check if browser is active."""
        return self._active

    def get_config(self) -> BrowserConfig:
        """Get current browser configuration."""
        return self._config

    def start_browser(self) -> tuple[bool, str]:
        """
        Start browser instance.

        Returns:
            Tuple of (success, message)
        """
        if not PLAYWRIGHT_AVAILABLE:
            return False, "Playwright 未安装。请运行: pip install playwright && playwright install"

        if self._active:
            return True, "浏览器已在运行"

        try:
            # Configure BrowserManager
            BrowserManager.configure(
                headless=self._config.headless,
                browser_type=self._config.browser_type,
                default_timeout=self._config.default_timeout,
                auto_screenshot=self._config.auto_screenshot,
            )

            # Pre-cache tools
            self._tools = get_browser_tools()

            self._active = True
            logger.info(f"Browser started: type={self._config.browser_type}, headless={self._config.headless}")
            return True, f"浏览器已启动 ({self._config.browser_type})"

        except Exception as e:
            logger.exception(f"Failed to start browser: {e}")
            return False, f"启动浏览器失败: {str(e)}"

    async def stop_browser(self) -> tuple[bool, str]:
        """
        Stop browser instance.

        Returns:
            Tuple of (success, message)
        """
        if not self._active:
            return True, "浏览器未运行"

        try:
            if BrowserManager:
                await BrowserManager.close()

            self._active = False
            self._tools = []
            logger.info("Browser stopped")
            return True, "浏览器已关闭"

        except Exception as e:
            logger.exception(f"Failed to stop browser: {e}")
            return False, f"关闭浏览器失败: {str(e)}"

    def get_browser_tools(self) -> list:
        """
        Get browser tools for AgentHarness.

        Returns:
            List of browser Tool instances
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available, returning empty tools list")
            return []

        if not self._tools:
            self._tools = get_browser_tools()

        return self._tools

    def get_status_text(self) -> str:
        """Get browser status text for UI display."""
        if not PLAYWRIGHT_AVAILABLE:
            return "浏览器不可用"

        if self._active:
            return f"浏览器: {self._config.browser_type} (运行中)"
        else:
            return "启动浏览器"

    def get_available_browsers(self) -> list[dict[str, str]]:
        """
        Get list of available browser options.

        Returns:
            List of browser options with display name and value
        """
        browsers = [
            {"value": "msedge", "label": "Microsoft Edge", "description": "系统自带，内网友好"},
            {"value": "chrome", "label": "Google Chrome", "description": "系统自带"},
            {"value": "chromium", "label": "Chromium", "description": "Playwright 自带"},
            {"value": "firefox", "label": "Firefox", "description": "Playwright 自带"},
        ]
        return browsers

    def detect_available_browser(self) -> str | None:
        """Detect the best available browser on the system."""
        if not PLAYWRIGHT_AVAILABLE or not BrowserManager:
            return None

        return BrowserManager.detect_available_browser()
