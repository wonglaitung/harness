"""
MCP Transport Layer.

Provides transport implementations for MCP protocol communication.
"""

from __future__ import annotations

import asyncio
import json
import os
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, AsyncIterator, Dict, Optional

if TYPE_CHECKING:
    import aiohttp


class MCPTransport(ABC):
    """
    MCP transport layer abstraction.

    Defines the interface for different transport mechanisms
    (stdio, HTTP, WebSocket, etc.)
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to MCP server."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to MCP server."""
        pass

    @abstractmethod
    async def send(self, message: dict) -> None:
        """
        Send a JSON-RPC message.

        Args:
            message: JSON-RPC message to send
        """
        pass

    @abstractmethod
    async def receive(self) -> AsyncIterator[dict]:
        """
        Receive messages from server.

        Yields:
            JSON-RPC messages received from server
        """
        pass

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if transport is connected."""
        pass


class StdioTransport(MCPTransport):
    """
    Standard input/output transport.

    Communicates with MCP server via subprocess stdin/stdout.
    This is the most common transport for local MCP servers.
    """

    def __init__(
        self,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ):
        """
        Initialize Stdio transport.

        Args:
            command: Command to execute (e.g., "mcp-server-filesystem")
            args: Command arguments
            env: Additional environment variables
        """
        self.command = command
        self.args = args or []
        self.env = env or {}
        self._process: Optional[asyncio.subprocess.Process] = None
        self._connected = False

    async def connect(self) -> None:
        """Start MCP server subprocess."""
        if self._process is not None:
            return

        # Merge environment variables
        full_env = {**os.environ, **self.env}

        # Create subprocess with process group for proper cleanup
        def preexec_fn():
            # Create new session and process group
            # This ensures child processes can be terminated together
            os.setsid()

        try:
            self._process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=full_env,
                preexec_fn=preexec_fn if os.name != "nt" else None,
            )
            self._connected = True
        except Exception as e:
            self._connected = False
            raise RuntimeError(f"Failed to start MCP server: {e}") from e

    async def disconnect(self) -> None:
        """Terminate MCP server subprocess."""
        if self._process is None:
            return

        self._connected = False

        # Try graceful termination first
        try:
            if os.name != "nt":
                # Send SIGTERM to process group
                os.killpg(os.getpgid(self._process.pid), 15)  # SIGTERM
            else:
                self._process.terminate()

            # Wait for process to exit (max 5 seconds)
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                # Force kill if still running
                if os.name != "nt":
                    os.killpg(os.getpgid(self._process.pid), 9)  # SIGKILL
                else:
                    self._process.kill()
                await self._process.wait()
        except ProcessLookupError:
            # Process already terminated
            pass
        finally:
            self._process = None

    async def send(self, message: dict) -> None:
        """Send message via stdin."""
        if self._process is None or self._process.stdin is None:
            raise RuntimeError("Transport not connected")

        # JSON-RPC messages are newline-delimited
        data = json.dumps(message) + "\n"
        self._process.stdin.write(data.encode("utf-8"))
        await self._process.stdin.drain()

    async def receive(self) -> AsyncIterator[dict]:
        """Receive messages from stdout."""
        if self._process is None or self._process.stdout is None:
            raise RuntimeError("Transport not connected")

        while True:
            try:
                line = await self._process.stdout.readline()
                if not line:
                    # EOF reached
                    break

                # Parse JSON-RPC message
                try:
                    message = json.loads(line.decode("utf-8").strip())
                    yield message
                except json.JSONDecodeError:
                    # Skip invalid messages
                    continue
            except asyncio.CancelledError:
                break

    @property
    def is_connected(self) -> bool:
        """Check if process is running."""
        return self._connected and self._process is not None

    async def check_stderr(self) -> str:
        """
        Check stderr for errors.

        Returns:
            stderr content if available
        """
        if self._process and self._process.stderr:
            stderr = await self._process.stderr.read(1024)
            return stderr.decode("utf-8", errors="replace")
        return ""


class HTTPTransport(MCPTransport):
    """
    HTTP/SSE transport.

    Communicates with MCP server via HTTP POST and Server-Sent Events.
    Suitable for remote MCP servers.
    """

    def __init__(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
    ):
        """
        Initialize HTTP transport.

        Args:
            url: MCP server base URL
            headers: Additional HTTP headers
            timeout: Request timeout in seconds
        """
        self.url = url
        self.headers = headers or {}
        self.timeout = timeout
        self._session: Optional["aiohttp.ClientSession"] = None
        self._sse_task: Optional[asyncio.Task] = None
        self._message_queue: asyncio.Queue[dict] = asyncio.Queue()
        self._connected = False

    async def connect(self) -> None:
        """Create HTTP session and start SSE listener."""
        if self._session is not None:
            return

        try:
            import aiohttp
        except ImportError:
            raise ImportError(
                "aiohttp is required for HTTP transport. "
                "Install with: pip install aiohttp"
            )

        self._session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=aiohttp.ClientTimeout(total=self.timeout),
        )
        self._connected = True

        # Start SSE listener in background
        self._sse_task = asyncio.create_task(self._sse_loop())

    async def disconnect(self) -> None:
        """Close HTTP session."""
        self._connected = False

        if self._sse_task:
            self._sse_task.cancel()
            try:
                await self._sse_task
            except asyncio.CancelledError:
                pass
            self._sse_task = None

        if self._session:
            await self._session.close()
            self._session = None

        # Clear message queue
        while not self._message_queue.empty():
            try:
                self._message_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def send(self, message: dict) -> None:
        """Send message via HTTP POST."""
        if self._session is None:
            raise RuntimeError("Transport not connected")

        import aiohttp

        try:
            async with self._session.post(
                f"{self.url}/message",
                json=message,
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Send failed: {resp.status} - {text}")
        except aiohttp.ClientError as e:
            raise RuntimeError(f"HTTP error: {e}") from e

    async def receive(self) -> AsyncIterator[dict]:
        """Receive messages from SSE queue."""
        while self._connected:
            try:
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0,
                )
                yield message
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    async def _sse_loop(self) -> None:
        """Background task to receive SSE messages."""
        if self._session is None:
            return

        import aiohttp

        try:
            async with self._session.get(f"{self.url}/sse") as resp:
                if resp.status != 200:
                    return

                async for line in resp.content:
                    if line.startswith(b"data: "):
                        try:
                            message = json.loads(line[6:].decode("utf-8"))
                            await self._message_queue.put(message)
                        except json.JSONDecodeError:
                            continue
        except asyncio.CancelledError:
            pass
        except aiohttp.ClientError:
            self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if session is active."""
        return self._connected and self._session is not None