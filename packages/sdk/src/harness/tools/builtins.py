"""
Built-in tools for file operations, search, and shell commands.
"""

import asyncio
import re
from collections.abc import Generator
from pathlib import Path
from typing import Any

from harness.tools.base import Tool, ToolContext
from harness.types import ToolResult


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

        try:
            # Find matches
            matches = list(base.glob(pattern))

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
            # Execute command
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
                content = output if output else "(no output)"

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
