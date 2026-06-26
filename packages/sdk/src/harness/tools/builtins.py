"""
Built-in tools for file operations, search, and shell commands.
"""

import asyncio
import logging
import platform
import re
import shutil
from collections.abc import Generator
from pathlib import Path
from typing import TYPE_CHECKING, Any

from harness.tools.base import Tool, ToolContext
from harness.types import ToolResult

if TYPE_CHECKING:
    from bs4 import NavigableString, Tag

logger = logging.getLogger(__name__)

# Cache for Windows shell availability
_WINDOWS_POWERSHELL_AVAILABLE: bool | None = None


def _get_windows_shell() -> tuple[str, list[str]]:
    """Determine the best shell for Windows.

    Returns:
        Tuple of (shell_executable, prefix_args)
        - PowerShell: ("powershell.exe", ["-Command"])
        - cmd: ("cmd.exe", ["/c"])
    """
    global _WINDOWS_POWERSHELL_AVAILABLE

    if _WINDOWS_POWERSHELL_AVAILABLE is None:
        # Check if PowerShell is available
        _WINDOWS_POWERSHELL_AVAILABLE = shutil.which("powershell.exe") is not None

    if _WINDOWS_POWERSHELL_AVAILABLE:
        return ("powershell.exe", ["-Command"])
    else:
        return ("cmd.exe", ["/c"])


class ReadTool(Tool):
    """Read file contents."""

    @property
    def name(self) -> str:
        return "read"

    @property
    def description(self) -> str:
        return "Read the contents of a file"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read",
                },
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of lines to read",
                },
            },
            "required": ["file_path"],
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        file_path = arguments["file_path"]
        offset = arguments.get("offset", 0)
        limit = arguments.get("limit")

        # Resolve path
        path = Path(file_path)
        if not path.is_absolute():
            path = context.working_directory / path

        # Check permissions
        if not context.permissions.is_path_allowed(str(path), "read"):
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Read access denied: {file_path}",
            )

        try:
            if not path.exists():
                return ToolResult(
                    tool_call_id="",
                    success=False,
                    content="",
                    error=f"File not found: {file_path}",
                )

            # Read file
            with open(path, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            # Apply offset and limit
            if offset:
                lines = lines[offset:]
            if limit:
                lines = lines[:limit]

            content = "".join(lines)

            return ToolResult(
                tool_call_id="",
                success=True,
                content=content,
            )

        except Exception as e:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Failed to read file: {str(e)}",
            )


class WriteTool(Tool):
    """Write content to a file."""

    @property
    def name(self) -> str:
        return "write"

    @property
    def description(self) -> str:
        return "Write content to a file"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to write",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write",
                },
            },
            "required": ["file_path", "content"],
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        file_path = arguments["file_path"]
        content = arguments["content"]

        # Resolve path
        path = Path(file_path)
        if not path.is_absolute():
            path = context.working_directory / path

        # Check permissions
        if not context.permissions.is_path_allowed(str(path), "write"):
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Write access denied: {file_path}",
            )

        try:
            # Create parent directories
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            return ToolResult(
                tool_call_id="",
                success=True,
                content=f"Successfully wrote {len(content)} bytes to {file_path}",
            )

        except Exception as e:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Failed to write file: {str(e)}",
            )


class EditTool(Tool):
    """Edit a file by replacing text."""

    @property
    def name(self) -> str:
        return "edit"

    @property
    def description(self) -> str:
        return "Edit a file by finding and replacing text"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to edit",
                },
                "old_text": {
                    "type": "string",
                    "description": "Text to find and replace",
                },
                "new_text": {
                    "type": "string",
                    "description": "Replacement text",
                },
            },
            "required": ["file_path", "old_text", "new_text"],
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        file_path = arguments["file_path"]
        old_text = arguments["old_text"]
        new_text = arguments["new_text"]

        # Resolve path
        path = Path(file_path)
        if not path.is_absolute():
            path = context.working_directory / path

        # Check permissions
        if not context.permissions.is_path_allowed(str(path), "write"):
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Write access denied: {file_path}",
            )

        try:
            # Read file
            with open(path, encoding="utf-8") as f:
                content = f.read()

            # Replace text
            if old_text not in content:
                return ToolResult(
                    tool_call_id="",
                    success=False,
                    content="",
                    error=f"Text not found in file: {old_text[:50]}...",
                )

            new_content = content.replace(old_text, new_text, 1)

            # Write file
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return ToolResult(
                tool_call_id="",
                success=True,
                content=f"Successfully edited {file_path}",
            )

        except Exception as e:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Failed to edit file: {str(e)}",
            )


class GlobTool(Tool):
    """Find files matching a pattern."""

    @property
    def name(self) -> str:
        return "glob"

    @property
    def description(self) -> str:
        return "Find files matching a glob pattern"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to match",
                },
                "path": {
                    "type": "string",
                    "description": "Base directory to search",
                },
            },
            "required": ["pattern"],
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        pattern = arguments["pattern"]
        base_path = arguments.get("path", str(context.working_directory))

        # Resolve base path
        base = Path(base_path)
        if not base.is_absolute():
            base = context.working_directory / base

        logger.debug(f"GlobTool: pattern={pattern}, base={base}, working_dir={context.working_directory}")

        try:
            # Find matches
            matches = list(base.glob(pattern))
            logger.debug(f"GlobTool: found {len(matches)} matches")

            # Format results
            if matches:
                content = "\n".join(str(m.relative_to(base)) for m in matches)
            else:
                content = "No files found"

            return ToolResult(
                tool_call_id="",
                success=True,
                content=content,
            )

        except Exception as e:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Failed to search: {str(e)}",
            )


class GrepTool(Tool):
    """Search for text in files."""

    @property
    def name(self) -> str:
        return "grep"

    @property
    def description(self) -> str:
        return "Search for text patterns in files"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Regex pattern to search for",
                },
                "path": {
                    "type": "string",
                    "description": "File or directory to search",
                },
            },
            "required": ["pattern"],
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        pattern = arguments["pattern"]
        search_path = arguments.get("path", str(context.working_directory))

        # Resolve path
        path = Path(search_path)
        if not path.is_absolute():
            path = context.working_directory / path

        try:
            regex = re.compile(pattern)
            results = []

            # Search in file or directory
            files: list[Path] | Generator[Path, None, None] = (
                [path] if path.is_file() else path.rglob("*")
            )

            for file_path in files:
                if not file_path.is_file():
                    continue

                try:
                    with open(file_path, encoding="utf-8", errors="replace") as f:
                        for i, line in enumerate(f, 1):
                            if regex.search(line):
                                rel_path = file_path.relative_to(context.working_directory)
                                results.append(f"{rel_path}:{i}: {line.rstrip()}")
                except Exception:
                    continue

            content = "\n".join(results) if results else "No matches found"

            return ToolResult(
                tool_call_id="",
                success=True,
                content=content,
            )

        except Exception as e:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Failed to search: {str(e)}",
            )


class BashTool(Tool):
    """Execute shell commands."""

    # Blocked commands for security
    BLOCKED_COMMANDS = {
        "rm -rf /",
        "mkfs",
        "dd if=",
        ":(){ :|:& };:",  # Fork bomb
    }

    @property
    def name(self) -> str:
        return "bash"

    @property
    def description(self) -> str:
        return "Execute a shell command"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds",
                },
            },
            "required": ["command"],
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        command = arguments["command"]
        timeout = arguments.get("timeout", 30)

        # Security check
        for blocked in self.BLOCKED_COMMANDS:
            if blocked in command:
                return ToolResult(
                    tool_call_id="",
                    success=False,
                    content="",
                    error=f"Blocked command: contains '{blocked}'",
                )

        # Check command permission
        if not context.permissions.is_command_allowed(command):
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Command not allowed: {command.split()[0]}",
            )

        try:
            # Execute command with platform-appropriate shell
            if platform.system() == "Windows":
                # Windows: Use PowerShell if available, fallback to cmd
                shell_exec, shell_args = _get_windows_shell()
                process = await asyncio.create_subprocess_exec(
                    shell_exec,
                    *shell_args,
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(context.working_directory),
                )
            else:
                # Unix: Use default shell
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(context.working_directory),
                )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )

            # Format output
            output = stdout.decode("utf-8", errors="replace")
            error_output = stderr.decode("utf-8", errors="replace")

            if process.returncode != 0:
                content = f"Exit code: {process.returncode}\n\n{output}"
                if error_output:
                    content += f"\n\nStderr:\n{error_output}"
            else:
                # Success - include output or a clear success message
                if output.strip():
                    content = output
                elif error_output.strip():
                    # Some tools output to stderr even on success
                    content = f"(success, stderr output)\n{error_output}"
                else:
                    content = "(command executed successfully, no output)"

            return ToolResult(
                tool_call_id="",
                success=process.returncode == 0,
                content=content,
                error=error_output if process.returncode != 0 else None,
            )

        except TimeoutError:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Command timed out after {timeout}s",
            )

        except Exception as e:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Failed to execute command: {str(e)}",
            )


class WebSearchTool(Tool):
    """Search the web for information."""

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Search the web for information using a search query"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (default 5)",
                },
            },
            "required": ["query"],
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        query = arguments["query"]
        num_results = arguments.get("num_results", 5)

        try:
            import aiohttp
        except ImportError:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error="aiohttp is required for web search. Install with: pip install aiohttp",
            )

        try:
            # Use DuckDuckGo Instant Answer API (free, no API key needed)
            async with aiohttp.ClientSession() as session:
                url = "https://api.duckduckgo.com/"
                params = {
                    "q": query,
                    "format": "json",
                    "no_html": 1,
                    "skip_disambig": 1,
                }

                async with session.get(url, params=params, timeout=30) as response:
                    if response.status != 200:
                        return ToolResult(
                            tool_call_id="",
                            success=False,
                            content="",
                            error=f"Search failed: HTTP {response.status}",
                        )

                    data = await response.json()

            # Format results
            results = []

            # Abstract (instant answer)
            if data.get("Abstract"):
                results.append(f"**Answer**: {data['Abstract']}")
                if data.get("AbstractURL"):
                    results.append(f"Source: {data['AbstractURL']}")

            # Related topics
            for topic in data.get("RelatedTopics", [])[:num_results]:
                if isinstance(topic, dict):
                    if "Text" in topic:
                        results.append(f"- {topic['Text']}")
                        if "FirstURL" in topic:
                            results.append(f"  URL: {topic['FirstURL']}")

            if not results:
                content = f"No results found for: {query}"
            else:
                content = "\n".join(results)

            return ToolResult(
                tool_call_id="",
                success=True,
                content=content,
            )

        except TimeoutError:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error="Search request timed out",
            )

        except Exception as e:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Search failed: {str(e)}",
            )


class WebFetchTool(Tool):
    """Fetch and extract content from a URL."""

    @property
    def name(self) -> str:
        return "web_fetch"

    @property
    def description(self) -> str:
        return "Fetch and extract text content from a URL"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL to fetch",
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector to extract specific content (optional)",
                },
                "max_length": {
                    "type": "integer",
                    "description": "Maximum content length in characters (default 10000)",
                },
            },
            "required": ["url"],
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        url = arguments["url"]
        selector = arguments.get("selector")
        max_length = arguments.get("max_length", 10000)

        try:
            import aiohttp
        except ImportError:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error="aiohttp is required for web fetch. Install with: pip install aiohttp",
            )

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (compatible; HarnessBot/1.0)",
                }

                async with session.get(
                    url, headers=headers, timeout=30
                ) as response:
                    if response.status != 200:
                        return ToolResult(
                            tool_call_id="",
                            success=False,
                            content="",
                            error=f"Fetch failed: HTTP {response.status}",
                        )

                    html = await response.text()

            # Try to use BeautifulSoup for parsing
            try:
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(html, "html.parser")

                # Remove script and style elements
                for element in soup(["script", "style", "nav", "footer", "header"]):
                    element.decompose()

                # Extract text
                if selector:
                    elements = soup.select(selector)
                    text = "\n\n".join(e.get_text(strip=True) for e in elements)
                else:
                    # Get main content
                    main = soup.find("main") or soup.find("article") or soup.find("body")
                    if main:
                        text = main.get_text(separator="\n", strip=True)
                    else:
                        text = soup.get_text(separator="\n", strip=True)

                # Clean up whitespace
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                text = "\n".join(lines)

            except ImportError:
                # Fallback to simple regex extraction
                import re

                # Remove script and style blocks
                html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
                html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL)

                # Remove HTML tags
                text = re.sub(r"<[^>]+>", " ", html)

                # Clean up whitespace
                text = re.sub(r"\s+", " ", text).strip()

            # Truncate if needed
            if len(text) > max_length:
                text = text[:max_length] + "\n\n... (truncated)"

            return ToolResult(
                tool_call_id="",
                success=True,
                content=text,
            )

        except TimeoutError:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error="Fetch request timed out",
            )

        except Exception as e:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Fetch failed: {str(e)}",
            )


class WebToMarkdownTool(Tool):
    """
    Fetch a webpage and convert to clean Markdown.

    Features:
    - Extracts main content (article, main, or body)
    - Converts HTML to clean Markdown
    - Preserves code blocks with syntax highlighting hints
    - Handles tables, lists, headings, links, images
    - Removes ads, navigation, footers
    """

    @property
    def name(self) -> str:
        return "web_to_markdown"

    @property
    def description(self) -> str:
        return "Fetch a webpage and convert it to clean Markdown format"

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL of the webpage to fetch and convert",
                },
                "selector": {
                    "type": "string",
                    "description": "CSS selector to extract specific content (optional, defaults to main content)",
                },
                "max_length": {
                    "type": "integer",
                    "description": "Maximum content length in characters (default 50000)",
                },
                "include_links": {
                    "type": "boolean",
                    "description": "Whether to preserve links (default true)",
                },
                "include_images": {
                    "type": "boolean",
                    "description": "Whether to include image references (default false)",
                },
            },
            "required": ["url"],
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        url = arguments["url"]
        selector = arguments.get("selector")
        max_length = arguments.get("max_length", 50000)
        include_links = arguments.get("include_links", True)
        include_images = arguments.get("include_images", False)

        try:
            import aiohttp
        except ImportError:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error="aiohttp is required. Install with: pip install aiohttp",
            )

        try:
            from bs4 import BeautifulSoup, NavigableString, Tag
        except ImportError:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error="beautifulsoup4 is required. Install with: pip install beautifulsoup4",
            )

        try:
            # Fetch the webpage
            async with aiohttp.ClientSession() as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (compatible; HarnessBot/1.0; +https://github.com/harness)",
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-US,en;q=0.9",
                }

                async with session.get(
                    url, headers=headers, timeout=30, allow_redirects=True
                ) as response:
                    if response.status != 200:
                        return ToolResult(
                            tool_call_id="",
                            success=False,
                            content="",
                            error=f"Fetch failed: HTTP {response.status}",
                        )

                    html = await response.text()

            # Parse HTML
            soup = BeautifulSoup(html, "html.parser")

            # Remove unwanted elements
            for element in soup([
                "script", "style", "nav", "footer", "header",
                "aside", "iframe", "noscript", "form",
                "button", "input", "select", "textarea",
            ]):
                element.decompose()

            # Remove elements with common ad/class names
            for class_name in ["ad", "ads", "advertisement", "sidebar", "comment", "comments", "social", "share", "related", "recommendation"]:
                for element in soup.find_all(class_=lambda x: x and class_name in str(x).lower()):
                    element.decompose()

            # Remove elements with ad-related IDs
            for id_pattern in ["ad", "ads", "sidebar", "comment"]:
                for element in soup.find_all(id=lambda x: x and id_pattern in str(x).lower()):
                    element.decompose()

            # Extract main content
            if selector:
                content_elements = soup.select(selector)
                if content_elements:
                    main_content = content_elements[0]
                else:
                    return ToolResult(
                        tool_call_id="",
                        success=False,
                        content="",
                        error=f"No elements found for selector: {selector}",
                    )
            else:
                # Try to find main content areas
                main_content = (
                    soup.find("article") or
                    soup.find("main") or
                    soup.find("div", class_=lambda x: x and any(c in str(x).lower() for c in ["content", "article", "post", "entry"])) or
                    soup.find("body")
                )

                if not main_content:
                    main_content = soup

            # Convert to Markdown
            markdown = self._html_to_markdown(main_content, include_links, include_images)

            # Extract title
            title = soup.find("title")
            if title:
                title_text = title.get_text(strip=True)
                markdown = f"# {title_text}\n\n{markdown}"

            # Add source URL
            markdown = f"[Source]({url})\n\n{markdown}"

            # Truncate if needed
            if len(markdown) > max_length:
                markdown = markdown[:max_length] + "\n\n... (truncated)"

            return ToolResult(
                tool_call_id="",
                success=True,
                content=markdown,
            )

        except asyncio.TimeoutError:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error="Fetch request timed out",
            )

        except Exception as e:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Failed to fetch and convert: {str(e)}",
            )

    def _html_to_markdown(
        self,
        element: "Tag | NavigableString",
        include_links: bool = True,
        include_images: bool = False,
    ) -> str:
        """Convert HTML element to Markdown."""
        if isinstance(element, NavigableString):
            text = str(element).strip()
            # Escape markdown special characters in plain text
            if text:
                # Don't escape in code blocks
                return text
            return ""

        if not isinstance(element, Tag):
            return ""

        tag_name = element.name.lower()

        # Skip certain elements
        if tag_name in ["script", "style", "nav", "footer", "header", "aside"]:
            return ""

        # Process children
        children_md = []
        for child in element.children:
            child_md = self._html_to_markdown(child, include_links, include_images)
            if child_md:
                children_md.append(child_md)

        children_text = "".join(children_md)

        # Convert based on tag type
        if tag_name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
            level = int(tag_name[1])
            # Get plain text for heading
            text = element.get_text(strip=True)
            return f"\n\n{'#' * level} {text}\n\n"

        elif tag_name == "p":
            text = element.get_text(strip=True)
            if text:
                return f"\n\n{text}\n\n"
            return ""

        elif tag_name == "br":
            return "\n"

        elif tag_name == "hr":
            return "\n\n---\n\n"

        elif tag_name in ["strong", "b"]:
            text = element.get_text(strip=True)
            if text:
                return f"**{text}**"
            return ""

        elif tag_name in ["em", "i"]:
            text = element.get_text(strip=True)
            if text:
                return f"*{text}*"
            return ""

        elif tag_name == "code":
            text = element.get_text()
            if "\n" in text:
                # Multi-line code block
                lang = element.get("class", [""])[0].replace("language-", "") if element.get("class") else ""
                return f"\n\n```{lang}\n{text}\n```\n\n"
            else:
                # Inline code
                return f"`{text}`"

        elif tag_name == "pre":
            # Get the code element inside if exists
            code_elem = element.find("code")
            if code_elem:
                code_text = code_elem.get_text()
                lang = ""
                if code_elem.get("class"):
                    for cls in code_elem.get("class", []):
                        if cls.startswith("language-"):
                            lang = cls.replace("language-", "")
                            break
                return f"\n\n```{lang}\n{code_text}\n```\n\n"
            else:
                text = element.get_text()
                return f"\n\n```\n{text}\n```\n\n"

        elif tag_name == "blockquote":
            lines = children_text.strip().split("\n")
            quoted = "\n".join(f"> {line}" for line in lines if line.strip())
            return f"\n\n{quoted}\n\n"

        elif tag_name == "a":
            if include_links:
                href = element.get("href", "")
                text = element.get_text(strip=True)
                if href and text:
                    return f"[{text}]({href})"
                return text
            else:
                return element.get_text(strip=True)

        elif tag_name == "img":
            if include_images:
                src = element.get("src", "")
                alt = element.get("alt", "image")
                if src:
                    # Handle relative URLs
                    if src.startswith("//"):
                        src = "https:" + src
                    return f"![{alt}]({src})"
            return ""

        elif tag_name == "ul":
            items = []
            for li in element.find_all("li", recursive=False):
                li_text = self._html_to_markdown(li, include_links, include_images).strip()
                if li_text:
                    items.append(f"- {li_text}")
            if items:
                return "\n\n" + "\n".join(items) + "\n\n"
            return ""

        elif tag_name == "ol":
            items = []
            for i, li in enumerate(element.find_all("li", recursive=False), 1):
                li_text = self._html_to_markdown(li, include_links, include_images).strip()
                if li_text:
                    items.append(f"{i}. {li_text}")
            if items:
                return "\n\n" + "\n".join(items) + "\n\n"
            return ""

        elif tag_name == "li":
            # Just return the content, parent handles formatting
            return children_text

        elif tag_name == "table":
            return self._table_to_markdown(element, include_links)

        elif tag_name in ["div", "section", "article", "main", "span"]:
            return children_text

        elif tag_name == "figure":
            return f"\n\n{children_text}\n\n"

        elif tag_name == "figcaption":
            text = element.get_text(strip=True)
            return f"*{text}*" if text else ""

        else:
            # Default: just return children's content
            return children_text

    def _table_to_markdown(self, table: "Tag", include_links: bool = True) -> str:
        """Convert HTML table to Markdown."""
        rows = []

        # Get all rows
        for tr in table.find_all("tr"):
            cells = []
            for cell in tr.find_all(["th", "td"]):
                cell_text = self._html_to_markdown(cell, include_links, False)
                # Clean up cell text
                cell_text = cell_text.replace("\n", " ").strip()
                cells.append(cell_text if cell_text else " ")

            if cells:
                rows.append(cells)

        if not rows:
            return ""

        # Build markdown table
        md_lines = []

        # First row as header
        if rows:
            header = rows[0]
            md_lines.append("| " + " | ".join(header) + " |")
            md_lines.append("| " + " | ".join(["---"] * len(header)) + " |")

            # Remaining rows
            for row in rows[1:]:
                # Pad row if needed
                while len(row) < len(header):
                    row.append(" ")
                md_lines.append("| " + " | ".join(row[:len(header)]) + " |")

        return "\n\n" + "\n".join(md_lines) + "\n\n"


class UpdateCoreMemoryTool(Tool):
    """
    Tool for Agent to update Core Memory (MEMORY.md).

    Allows the Agent to persist user preferences, project conventions,
    and important decisions to long-term memory.

    This tool should be explicitly added to the tools list (Mem0 pattern).

    Example:
        agent = AgentHarness(
            tools=[UpdateCoreMemoryTool()],
        )
    """

    @property
    def name(self) -> str:
        return "update_core_memory"

    @property
    def description(self) -> str:
        return (
            "更新用户偏好或项目约定到长期记忆。\n\n"
            "重要规则：\n"
            "1. **提炼内容**：不要存储用户原话，要提炼成简洁的陈述\n"
            "   - 用户说「使用 cmd，不要用 powershell」→ 存储「Shell：使用 cmd（不使用 PowerShell）」\n"
            "   - 用户说「我使用 Windows」→ 存储「操作系统：Windows」\n"
            "2. **避免重复**：添加前先检查是否已有类似记忆，如有则不要重复添加\n"
            "3. **适用场景**：用户提到长期偏好、工作环境、项目约束等\n\n"
            "示例：\n"
            "- 用户：「我习惯用深色主题」→ category=user_profile, content=\"主题偏好：深色\"\n"
            "- 用户：「以后回复简短一点」→ category=learned_patterns, content=\"回复风格：简洁\""
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": [
                        "user_profile",
                        "key_decisions",
                        "learned_patterns",
                        "project_context",
                    ],
                    "description": "记忆类别",
                },
                "content": {
                    "type": "string",
                    "description": "记忆内容",
                },
                "action": {
                    "type": "string",
                    "enum": ["add", "remove"],
                    "description": "操作类型",
                },
            },
            "required": ["category", "content", "action"],
        }

    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        from harness.memory.memory_file import (
            MemoryCategory,
            MemoryEntry,
            MemoryFileManager,
            MemorySource,
        )

        category_str = arguments["category"]
        content = arguments["content"]
        action = arguments["action"]

        try:
            category = MemoryCategory(category_str)
        except ValueError:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"Invalid category: {category_str}. "
                f"Must be one of: user_profile, key_decisions, learned_patterns, project_context",
            )

        # Get MemoryFileManager - use configured path or global ~/.harness/
        from harness.tools.permissions import get_harness_config_dir

        # Priority: 1) context metadata, 2) config default (~/.harness/)
        global_memory_root = context.metadata.get("memory_md_path") or get_harness_config_dir()
        manager = MemoryFileManager(project_root=global_memory_root)

        if action == "add":
            entry = MemoryEntry(
                category=category,
                content=content,
                source=MemorySource.USER_INPUT,
            )
            added = manager.add_entry(entry)
            if added:
                return ToolResult(
                    tool_call_id="",
                    success=True,
                    content=f"已添加到 {category.value}: {content}",
                    metadata={"refresh_memory": True},  # Signal UI to refresh
                )
            else:
                return ToolResult(
                    tool_call_id="",
                    success=True,
                    content=f"跳过重复记忆: 已有类似内容",
                )

        elif action == "remove":
            # Find and remove matching entry
            entries = manager.get_entries(category)
            for i, entry_content in enumerate(entries):
                if content in entry_content:
                    manager.remove_entry(category, i)
                    return ToolResult(
                        tool_call_id="",
                        success=True,
                        content=f"已从 {category.value} 移除: {entry_content}",
                        metadata={"refresh_memory": True},  # Signal UI to refresh
                    )

            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"未找到匹配的记忆: {content}",
            )

        return ToolResult(
            tool_call_id="",
            success=False,
            content="",
            error=f"Unknown action: {action}",
        )
