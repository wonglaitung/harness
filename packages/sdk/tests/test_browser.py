"""
Tests for browser automation tools.

Note: These tests require Playwright to be installed:
    pip install playwright && playwright install
"""

import pytest

from harness.tools.base import ToolContext
from harness.tools.browser import (
    BrowserClickTool,
    BrowserCloseTool,
    BrowserExtractTool,
    BrowserManager,
    BrowserNavigateTool,
    BrowserScreenshotTool,
    BrowserTypeTool,
    BrowserWaitTool,
    get_browser_tools,
)

# Skip all tests if Playwright is not installed
pytest.importorskip("playwright", reason="Playwright not installed")


# Test fixtures
@pytest.fixture
def context():
    """Create a tool context for testing."""
    from pathlib import Path

    from harness.tools.permissions import PermissionSet

    return ToolContext(
        session_id="test-session",
        working_directory=Path.cwd(),
        permissions=PermissionSet(),
    )


@pytest.fixture(autouse=True)
async def cleanup_browser():
    """Ensure browser is closed after each test."""
    yield
    await BrowserManager.close()


class TestBrowserManager:
    """Tests for BrowserManager singleton."""

    @pytest.mark.asyncio
    async def test_get_page_creates_browser(self):
        """Test that get_page creates a browser instance."""
        page = await BrowserManager.get_page()
        assert page is not None
        assert not page.is_closed()
        assert BrowserManager.is_active()

    @pytest.mark.asyncio
    async def test_singleton_pattern(self):
        """Test that BrowserManager is a singleton."""
        manager1 = BrowserManager()
        manager2 = BrowserManager()
        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_close_browser(self):
        """Test closing the browser."""
        await BrowserManager.get_page()
        await BrowserManager.close()
        assert not BrowserManager.is_active()

    @pytest.mark.asyncio
    async def test_take_screenshot(self):
        """Test taking a screenshot."""
        page = await BrowserManager.get_page()
        await page.goto("data:text/html,<h1>Test</h1>")

        screenshot_path = await BrowserManager.take_screenshot("test")
        assert screenshot_path is not None


class TestBrowserNavigateTool:
    """Tests for BrowserNavigateTool."""

    @pytest.mark.asyncio
    async def test_navigate_to_url(self, context):
        """Test navigating to a URL."""
        tool = BrowserNavigateTool()

        # Use data URL for testing without network
        html = (
            "<html><head><title>Test Page</title></head>"
            "<body><h1>Hello</h1></body></html>"
        )
        result = await tool.execute({"url": f"data:text/html,{html}"}, context)

        assert result.success
        assert "Test Page" in result.content

    @pytest.mark.asyncio
    async def test_navigate_with_custom_wait(self, context):
        """Test navigating with custom wait_until."""
        tool = BrowserNavigateTool()

        result = await tool.execute(
            {"url": "data:text/html,<h1>Test</h1>", "wait_until": "domcontentloaded"}, context
        )

        assert result.success

    @pytest.mark.asyncio
    async def test_navigate_invalid_url(self, context):
        """Test navigating to an invalid URL."""
        tool = BrowserNavigateTool()

        result = await tool.execute({"url": "not-a-valid-url"}, context)

        # Should fail gracefully
        assert result.success is False


class TestBrowserClickTool:
    """Tests for BrowserClickTool."""

    @pytest.mark.asyncio
    async def test_click_element(self, context):
        """Test clicking an element."""
        # Navigate to a test page
        nav_tool = BrowserNavigateTool()
        html = "<button id='btn' onclick='this.innerText=\"Clicked\"'>Click Me</button>"
        await nav_tool.execute({"url": f"data:text/html,{html}"}, context)

        click_tool = BrowserClickTool()
        result = await click_tool.execute({"selector": "#btn"}, context)

        assert result.success

    @pytest.mark.asyncio
    async def test_click_with_retry(self, context):
        """Test click retry on failure."""
        nav_tool = BrowserNavigateTool()
        await nav_tool.execute({"url": "data:text/html,<div id='btn'>Click</div>"}, context)

        click_tool = BrowserClickTool()
        result = await click_tool.execute(
            {"selector": "#nonexistent", "timeout": 1000, "retry_count": 0}, context
        )

        assert result.success is False
        assert "not found" in result.error.lower() or "timeout" in result.error.lower()


class TestBrowserTypeTool:
    """Tests for BrowserTypeTool."""

    @pytest.mark.asyncio
    async def test_type_into_input(self, context):
        """Test typing into an input field."""
        nav_tool = BrowserNavigateTool()
        await nav_tool.execute({"url": "data:text/html,<input id='input' type='text' />"}, context)

        type_tool = BrowserTypeTool()
        result = await type_tool.execute({"selector": "#input", "text": "Hello World"}, context)

        assert result.success

    @pytest.mark.asyncio
    async def test_type_with_clear(self, context):
        """Test typing with clear_first option."""
        nav_tool = BrowserNavigateTool()
        await nav_tool.execute(
            {"url": "data:text/html,<input id='input' value='existing' />"}, context
        )

        type_tool = BrowserTypeTool()
        result = await type_tool.execute(
            {"selector": "#input", "text": "new text", "clear_first": True}, context
        )

        assert result.success


class TestBrowserExtractTool:
    """Tests for BrowserExtractTool."""

    @pytest.mark.asyncio
    async def test_extract_text(self, context):
        """Test extracting text content."""
        nav_tool = BrowserNavigateTool()
        await nav_tool.execute(
            {"url": "data:text/html,<div id='content'>Hello World</div>"}, context
        )

        extract_tool = BrowserExtractTool()
        result = await extract_tool.execute({"selector": "#content"}, context)

        assert result.success
        assert "Hello World" in result.content

    @pytest.mark.asyncio
    async def test_extract_attribute(self, context):
        """Test extracting an attribute."""
        nav_tool = BrowserNavigateTool()
        await nav_tool.execute(
            {"url": "data:text/html,<a id='link' href='https://example.com'>Link</a>"}, context
        )

        extract_tool = BrowserExtractTool()
        result = await extract_tool.execute({"selector": "#link", "attribute": "href"}, context)

        assert result.success
        assert "https://example.com" in result.content

    @pytest.mark.asyncio
    async def test_extract_multiple(self, context):
        """Test extracting multiple elements."""
        nav_tool = BrowserNavigateTool()
        html = (
            "<ul><li class='item'>A</li>"
            "<li class='item'>B</li>"
            "<li class='item'>C</li></ul>"
        )
        await nav_tool.execute({"url": f"data:text/html,{html}"}, context)

        extract_tool = BrowserExtractTool()
        result = await extract_tool.execute({"selector": ".item", "multiple": True}, context)

        assert result.success
        assert result.metadata["count"] == 3


class TestBrowserScreenshotTool:
    """Tests for BrowserScreenshotTool."""

    @pytest.mark.asyncio
    async def test_take_screenshot(self, context):
        """Test taking a screenshot."""
        nav_tool = BrowserNavigateTool()
        await nav_tool.execute({"url": "data:text/html,<h1>Screenshot Test</h1>"}, context)

        screenshot_tool = BrowserScreenshotTool()
        result = await screenshot_tool.execute({}, context)

        assert result.success
        assert result.metadata.get("path") is not None

    @pytest.mark.asyncio
    async def test_take_element_screenshot(self, context):
        """Test taking a screenshot of a specific element."""
        nav_tool = BrowserNavigateTool()
        html = (
            "<div id='box' style='width:100px;height:100px;background:red;'>"
            "Box</div>"
        )
        await nav_tool.execute({"url": f"data:text/html,{html}"}, context)

        screenshot_tool = BrowserScreenshotTool()
        result = await screenshot_tool.execute({"selector": "#box"}, context)

        assert result.success

    @pytest.mark.asyncio
    async def test_return_base64(self, context):
        """Test returning base64 encoded screenshot."""
        nav_tool = BrowserNavigateTool()
        await nav_tool.execute({"url": "data:text/html,<h1>Test</h1>"}, context)

        screenshot_tool = BrowserScreenshotTool()
        result = await screenshot_tool.execute({"return_base64": True}, context)

        assert result.success
        assert "base64" in result.metadata


class TestBrowserWaitTool:
    """Tests for BrowserWaitTool."""

    @pytest.mark.asyncio
    async def test_wait_for_selector(self, context):
        """Test waiting for an element to appear."""
        nav_tool = BrowserNavigateTool()
        await nav_tool.execute({"url": "data:text/html,<div id='target'>Target</div>"}, context)

        wait_tool = BrowserWaitTool()
        result = await wait_tool.execute(
            {"wait_type": "selector", "selector": "#target", "state": "visible"}, context
        )

        assert result.success

    @pytest.mark.asyncio
    async def test_wait_for_timeout(self, context):
        """Test waiting for a timeout."""
        wait_tool = BrowserWaitTool()

        import time

        start = time.time()
        result = await wait_tool.execute({"wait_type": "timeout", "timeout_ms": 500}, context)
        elapsed = time.time() - start

        assert result.success
        assert elapsed >= 0.4  # Allow some tolerance


class TestBrowserCloseTool:
    """Tests for BrowserCloseTool."""

    @pytest.mark.asyncio
    async def test_close_browser(self, context):
        """Test closing the browser."""
        # First open a browser
        nav_tool = BrowserNavigateTool()
        await nav_tool.execute({"url": "data:text/html,<h1>Test</h1>"}, context)

        assert BrowserManager.is_active()

        # Now close it
        close_tool = BrowserCloseTool()
        result = await close_tool.execute({}, context)

        assert result.success
        assert not BrowserManager.is_active()


class TestGetBrowserTools:
    """Tests for get_browser_tools function."""

    def test_returns_all_tools(self):
        """Test that get_browser_tools returns all tools."""
        tools = get_browser_tools()

        assert len(tools) == 7
        tool_names = [t.name for t in tools]
        assert "browser_navigate" in tool_names
        assert "browser_click" in tool_names
        assert "browser_type" in tool_names
        assert "browser_extract" in tool_names
        assert "browser_screenshot" in tool_names
        assert "browser_wait" in tool_names
        assert "browser_close" in tool_names


class TestXPathSelectors:
    """Tests for XPath selector support."""

    @pytest.mark.asyncio
    async def test_click_with_xpath(self, context):
        """Test clicking using XPath selector."""
        nav_tool = BrowserNavigateTool()
        await nav_tool.execute({"url": "data:text/html,<button>Submit</button>"}, context)

        click_tool = BrowserClickTool()
        result = await click_tool.execute({"selector": "//button[text()='Submit']"}, context)

        assert result.success

    @pytest.mark.asyncio
    async def test_extract_with_xpath(self, context):
        """Test extracting using XPath selector."""
        nav_tool = BrowserNavigateTool()
        await nav_tool.execute(
            {"url": "data:text/html,<div><span class='name'>John</span></div>"}, context
        )

        extract_tool = BrowserExtractTool()
        result = await extract_tool.execute({"selector": "//span[@class='name']"}, context)

        assert result.success
        assert "John" in result.content


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_playwright_not_installed_error(self, context, monkeypatch):
        """Test error when Playwright is not installed."""
        import harness.tools.browser as browser_module

        original_value = browser_module.PLAYWRIGHT_AVAILABLE

        try:
            browser_module.PLAYWRIGHT_AVAILABLE = False
            await BrowserManager.close()  # Ensure clean state

            tool = BrowserNavigateTool()
            result = await tool.execute({"url": "https://example.com"}, context)

            assert result.success is False
            assert "not installed" in result.error.lower()
        finally:
            browser_module.PLAYWRIGHT_AVAILABLE = original_value

    @pytest.mark.asyncio
    async def test_element_not_found_error(self, context):
        """Test error when element is not found."""
        nav_tool = BrowserNavigateTool()
        await nav_tool.execute({"url": "data:text/html,<div>No button here</div>"}, context)

        click_tool = BrowserClickTool()
        result = await click_tool.execute(
            {"selector": "#nonexistent", "timeout": 1000, "retry_count": 0}, context
        )

        assert result.success is False
