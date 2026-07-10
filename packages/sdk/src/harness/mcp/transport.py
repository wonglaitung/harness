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

        # Debug: log environment variables
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"[StdioTransport] Environment variables passed to subprocess: {list(self.env.keys())}")
        if self.env:
            for k, v in self.env.items():
                # Mask sensitive values
                if 'KEY' in k.upper() or 'SECRET' in k.upper() or 'TOKEN' in k.upper():
                    logger.debug(f"[StdioTransport]   {k}=***{v[-4:] if len(v) > 4 else '****'}")
                else:
                    logger.debug(f"[StdioTransport]   {k}={v}")

        # Create subprocess with process group for proper cleanup
        def preexec_fn():
            # Create new session and process group
            # This ensures child processes can be terminated together
            os.setsid()

        logger.info(f"[StdioTransport] Starting MCP server: {self.command} {' '.join(self.args)}")
        logger.debug(f"[StdioTransport] Full command: {self.command} with args {self.args}")

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
            logger.info(f"[StdioTransport] MCP server started with PID: {self._process.pid}")

            # Check if process is still running after a short delay
            await asyncio.sleep(0.1)
            if self._process.returncode is not None:
                # Process exited immediately - read stderr for error
                stderr = await self._process.stderr.read()
                stderr_text = stderr.decode("utf-8", errors="replace") if stderr else ""
                logger.error(f"[StdioTransport] Process exited immediately with code {self._process.returncode}")
                logger.error(f"[StdioTransport] stderr: {stderr_text}")
                raise RuntimeError(f"MCP server process exited immediately (code {self._process.returncode}): {stderr_text}")

            self._connected = True
            logger.debug(f"[StdioTransport] Process is running, stdin/stdout pipes ready")
        except Exception as e:
            self._connected = False
            logger.error(f"[StdioTransport] Failed to start MCP server: {e}")
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
        import logging
        logger = logging.getLogger(__name__)

        if self._process is None or self._process.stdin is None:
            logger.error(f"[StdioTransport] send() called but process not connected")
            raise RuntimeError("Transport not connected")

        # Debug: check if process is still running
        if self._process.returncode is not None:
            logger.error(f"[StdioTransport] Process already exited with code {self._process.returncode}")
            raise RuntimeError(f"Process exited with code {self._process.returncode}")

        # JSON-RPC messages are newline-delimited
        data = json.dumps(message) + "\n"
        logger.debug(f"[StdioTransport] Sending message: {message.get('method', 'unknown')} (id={message.get('id', 'none')})")
        logger.debug(f"[StdioTransport] Raw data: {data.strip()[:200]}...")
        self._process.stdin.write(data.encode("utf-8"))
        await self._process.stdin.drain()
        logger.debug(f"[StdioTransport] Message sent successfully")

    async def receive(self) -> AsyncIterator[dict]:
        """Receive messages from stdout."""
        import logging
        logger = logging.getLogger(__name__)

        if self._process is None or self._process.stdout is None:
            logger.error(f"[StdioTransport] receive() called but process not connected")
            raise RuntimeError("Transport not connected")

        logger.debug(f"[StdioTransport] Starting receive loop")
        while True:
            try:
                line = await self._process.stdout.readline()
                if not line:
                    # EOF reached
                    logger.warning(f"[StdioTransport] EOF reached on stdout, process may have exited")
                    # Check process status
                    if self._process.returncode is not None:
                        logger.error(f"[StdioTransport] Process exited with code {self._process.returncode}")
                    break

                # Debug: log raw line
                line_text = line.decode("utf-8").strip()
                logger.debug(f"[StdioTransport] Received line: {line_text[:200]}...")

                # Parse JSON-RPC message
                try:
                    message = json.loads(line_text)
                    logger.debug(f"[StdioTransport] Parsed message: method={message.get('method', 'n/a')}, id={message.get('id', 'n/a')}")
                    yield message
                except json.JSONDecodeError as e:
                    # Skip invalid messages
                    logger.warning(f"[StdioTransport] JSON decode error: {e}, line: {line_text[:100]}")
                    continue
            except asyncio.CancelledError:
                logger.debug(f"[StdioTransport] Receive loop cancelled")
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
    HTTP/SSE transport supporting multiple MCP protocol versions.

    Supports three transport modes:
    1. Streamable HTTP (2025-11-25): POST to single endpoint, response may be SSE
    2. HTTP+SSE (2024-11-05, deprecated): POST /message + GET /sse separately
    3. FastMCP SSE: GET /sse discovers endpoint, POST to /messages/?session_id=xxx

    Auto-detects protocol on connect:
    - Try POST to /mcp first (Streamable HTTP)
    - If 404/405, fallback to GET /sse (HTTP+SSE or FastMCP)
    """

    # Protocol detection results
    PROTOCOL_STREAMABLE_HTTP = "streamable-http"
    PROTOCOL_HTTP_SSE = "http-sse"  # Legacy deprecated
    PROTOCOL_FASTMCP_SSE = "fastmcp-sse"

    def __init__(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
        protocol: str | None = None,  # Force specific protocol
    ):
        """
        Initialize HTTP transport.

        Args:
            url: MCP server base URL
            headers: Additional HTTP headers
            timeout: Request timeout in seconds
            protocol: Force specific protocol (auto-detect if None)
        """
        self.url = url.rstrip("/")
        self.headers = headers or {}
        self.timeout = timeout
        self._forced_protocol = protocol
        self._protocol: Optional[str] = None
        self._session: Optional["aiohttp.ClientSession"] = None
        self._sse_session: Optional["aiohttp.ClientSession"] = None  # Separate session for SSE streams
        self._sse_task: Optional[asyncio.Task] = None
        self._message_queue: asyncio.Queue[dict] = asyncio.Queue()
        self._connected = False
        self._endpoint_ready: asyncio.Event = asyncio.Event()
        self._message_endpoint: Optional[str] = None  # For FastMCP dynamic endpoint
        self._session_id: Optional[str] = None  # For Streamable HTTP session

    async def connect(self) -> None:
        """Create HTTP session and detect/establish connection."""
        if self._session is not None:
            return

        try:
            import aiohttp
        except ImportError:
            raise ImportError(
                "aiohttp is required for HTTP transport. "
                "Install with: pip install aiohttp"
            )

        # Create separate session for SSE streams with unlimited total timeout
        # SSE is a long-lived connection that shouldn't have a total time limit
        self._sse_session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=aiohttp.ClientTimeout(
                total=None,      # No total timeout for SSE streams
                sock_read=None,  # No timeout for SSE reads
            ),
        )

        # Regular session for POST requests with configurable timeout
        self._session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=aiohttp.ClientTimeout(
                total=self.timeout,
                sock_connect=self.timeout,  # Connection timeout
            ),
        )

        try:
            # Detect protocol if not forced
            if self._forced_protocol:
                self._protocol = self._forced_protocol
            else:
                self._protocol = await self._detect_protocol()

            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Detected MCP protocol: {self._protocol}")

            # Establish connection based on protocol
            if self._protocol == self.PROTOCOL_STREAMABLE_HTTP:
                # Streamable HTTP: start optional GET SSE stream for server push
                self._message_endpoint = "/mcp"
                self._sse_task = asyncio.create_task(self._streamable_sse_loop())
                self._endpoint_ready.set()
                self._connected = True
            else:
                # HTTP+SSE or FastMCP: start SSE listener
                self._sse_task = asyncio.create_task(self._sse_loop())
                await asyncio.wait_for(self._endpoint_ready.wait(), timeout=10.0)
                self._connected = True

        except asyncio.TimeoutError:
            if self._sse_task:
                self._sse_task.cancel()
            raise RuntimeError("Timeout waiting for SSE endpoint discovery")
        except Exception:
            if self._session:
                await self._session.close()
                self._session = None
            raise

    async def _detect_protocol(self) -> str:
        """
        Detect server's HTTP transport protocol.

        Strategy per MCP spec:
        1. POST initialize to /mcp with Accept: application/json, text/event-stream
        2. If 200 OK: Streamable HTTP (new standard)
        3. If 400/404/405: fallback to HTTP+SSE (legacy)

        Returns:
            Protocol type constant
        """
        import aiohttp
        import logging
        logger = logging.getLogger(__name__)

        init_msg = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "harness", "version": "1.0"}
            },
            "id": 1
        }

        # Try Streamable HTTP endpoint first
        try:
            async with self._session.post(
                f"{self.url}/mcp",
                json=init_msg,
                headers={"Accept": "application/json, text/event-stream"},
            ) as resp:
                if resp.status == 200:
                    # Check response type
                    content_type = resp.headers.get("Content-Type", "")
                    if "text/event-stream" in content_type:
                        # Server returned SSE stream - need to consume it
                        logger.info("Server supports Streamable HTTP with SSE response")
                        # Parse initial response from SSE
                        await self._parse_sse_response(resp)
                        return self.PROTOCOL_STREAMABLE_HTTP
                    else:
                        # Plain JSON response
                        response = await resp.json()
                        await self._message_queue.put(response)
                        # Extract session ID if provided
                        self._session_id = resp.headers.get("Mcp-Session-Id")
                        logger.info("Server supports Streamable HTTP with JSON response")
                        return self.PROTOCOL_STREAMABLE_HTTP
                elif resp.status in (400, 404, 405):
                    # Server doesn't support Streamable HTTP, fallback to SSE
                    logger.info(f"Server returned {resp.status}, falling back to SSE")
                else:
                    logger.warning(f"Unexpected status {resp.status} from /mcp")
        except aiohttp.ClientError as e:
            logger.debug(f"POST to /mcp failed: {e}")

        # Fallback: GET /sse to check if it's FastMCP or legacy HTTP+SSE
        try:
            async with self._session.get(f"{self.url}/sse") as resp:
                if resp.status == 200:
                    # Read first event to determine subtype
                    content_type = resp.headers.get("Content-Type", "")
                    if "text/event-stream" in content_type:
                        # Check for FastMCP endpoint event
                        async for line in resp.content:
                            line = line.decode("utf-8").strip()
                            if line.startswith("event:"):
                                event_type = line[6:].strip()
                                if event_type == "endpoint":
                                    # FastMCP style
                                    logger.info("Detected FastMCP SSE protocol")
                                    return self.PROTOCOL_FASTMCP_SSE
                            elif line.startswith("data:"):
                                # Could be legacy HTTP+SSE starting with JSON-RPC
                                logger.info("Detected legacy HTTP+SSE protocol")
                                return self.PROTOCOL_HTTP_SSE
                            break  # Only check first event
        except aiohttp.ClientError as e:
            logger.debug(f"GET /sse failed: {e}")

        # Default to FastMCP SSE (most common for current servers)
        logger.info("Defaulting to FastMCP SSE protocol")
        return self.PROTOCOL_FASTMCP_SSE

    async def _parse_sse_response(self, resp) -> None:
        """Parse SSE stream from Streamable HTTP response."""
        current_event = None
        async for line in resp.content:
            line = line.decode("utf-8").strip()
            if line.startswith("event:"):
                current_event = line[6:].strip()
            elif line.startswith("data:"):
                data = line[5:].strip()
                try:
                    message = json.loads(data)
                    await self._message_queue.put(message)
                except json.JSONDecodeError:
                    pass
            elif not line:
                current_event = None

    async def disconnect(self) -> None:
        """Close HTTP sessions."""
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

        if self._sse_session:
            await self._sse_session.close()
            self._sse_session = None

        # Clear message queue
        while not self._message_queue.empty():
            try:
                self._message_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    async def send(self, message: dict, _reconnect_attempt: int = 0) -> None:
        """
        Send message via HTTP POST.

        Protocol-specific behavior:
        - Streamable HTTP: POST to /mcp, may return SSE stream
        - HTTP+SSE: POST to /message
        - FastMCP: POST to discovered /messages/?session_id=xxx

        Automatically reconnects on session expiry (404) for SSE protocols.
        """
        if self._session is None:
            raise RuntimeError("Transport not connected")

        import aiohttp
        import logging
        logger = logging.getLogger(__name__)

        endpoint = self._get_send_endpoint()
        headers = self._get_send_headers()

        try:
            async with self._session.post(
                f"{self.url}{endpoint}",
                json=message,
                headers=headers,
            ) as resp:
                if resp.status == 404 and self._protocol == self.PROTOCOL_FASTMCP_SSE:
                    # Session expired - reconnect and retry (once)
                    if _reconnect_attempt == 0:
                        logger.info("FastMCP session expired, reconnecting...")
                        await self._reconnect_fkmcp()
                        # Retry with new session
                        return await self.send(message, _reconnect_attempt=1)
                    else:
                        raise RuntimeError("Session expired after reconnect attempt")

                if resp.status not in (200, 202):
                    text = await resp.text()
                    raise RuntimeError(f"Send failed: {resp.status} - {text}")

                # Streamable HTTP may return SSE stream
                if self._protocol == self.PROTOCOL_STREAMABLE_HTTP:
                    content_type = resp.headers.get("Content-Type", "")
                    if "text/event-stream" in content_type:
                        # Parse SSE response
                        await self._parse_sse_response(resp)
                    elif resp.status == 200:
                        # Plain JSON response
                        try:
                            response = await resp.json()
                            await self._message_queue.put(response)
                        except:
                            pass  # No JSON body

                    # Update session ID if provided
                    new_session_id = resp.headers.get("Mcp-Session-Id")
                    if new_session_id:
                        self._session_id = new_session_id

        except aiohttp.ClientError as e:
            raise RuntimeError(f"HTTP error: {e}") from e

    async def _reconnect_fkmcp(self) -> None:
        """
        Reconnect FastMCP SSE session.

        Called when POST returns 404 (session expired).
        Restarts SSE listener to get new session_id.
        """
        import logging
        logger = logging.getLogger(__name__)

        # Cancel existing SSE task
        if self._sse_task:
            self._sse_task.cancel()
            try:
                await self._sse_task
            except asyncio.CancelledError:
                pass

        # Reset endpoint discovery
        self._message_endpoint = None
        self._endpoint_ready.clear()

        # Ensure SSE session exists
        if self._sse_session is None or self._sse_session.closed:
            try:
                import aiohttp
            except ImportError:
                raise ImportError("aiohttp is required for HTTP transport")
            self._sse_session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(
                    total=None,      # No total timeout for SSE streams
                    sock_read=None,  # No timeout for SSE reads
                ),
            )
            logger.info("Created new SSE session for reconnection")

        # Start new SSE listener
        self._sse_task = asyncio.create_task(self._sse_loop())

        # Wait for new endpoint
        try:
            await asyncio.wait_for(self._endpoint_ready.wait(), timeout=10.0)
            logger.info(f"Reconnected with new endpoint: {self._message_endpoint}")
        except asyncio.TimeoutError:
            raise RuntimeError("Timeout waiting for SSE reconnection")

    def _get_send_endpoint(self) -> str:
        """Get the POST endpoint based on protocol."""
        if self._protocol == self.PROTOCOL_STREAMABLE_HTTP:
            return "/mcp"
        elif self._protocol == self.PROTOCOL_HTTP_SSE:
            return "/message"
        elif self._protocol == self.PROTOCOL_FASTMCP_SSE:
            if self._message_endpoint is None:
                raise RuntimeError("FastMCP endpoint not discovered")
            return self._message_endpoint
        else:
            return self._message_endpoint or "/message"

    def _get_send_headers(self) -> dict:
        """Get headers for POST request based on protocol."""
        headers = {}
        if self._protocol == self.PROTOCOL_STREAMABLE_HTTP:
            # Accept both JSON and SSE responses
            headers["Accept"] = "application/json, text/event-stream"
            if self._session_id:
                headers["Mcp-Session-Id"] = self._session_id
        return headers

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
        """
        Background task to maintain SSE connection for HTTP+SSE and FastMCP.

        Handles both HTTP+SSE (legacy) and FastMCP SSE:
        - FastMCP: event: endpoint -> discover /messages/?session_id=xxx
        - HTTP+SSE: direct JSON-RPC messages in data: lines
        """
        if self._sse_session is None:
            return

        import aiohttp
        import logging
        logger = logging.getLogger(__name__)

        try:
            async with self._sse_session.get(f"{self.url}/sse") as resp:
                if resp.status != 200:
                    logger.error(f"SSE endpoint returned {resp.status}")
                    self._endpoint_ready.set()
                    return

                current_event = None
                async for line in resp.content:
                    line = line.decode("utf-8").strip()

                    # Skip SSE comment lines (ping)
                    if line.startswith(":"):
                        continue

                    # Parse SSE format
                    if line.startswith("event:"):
                        current_event = line[6:].strip()
                    elif line.startswith("data:"):
                        data = line[5:].strip()

                        # FastMCP endpoint discovery
                        if current_event == "endpoint" and data.startswith("/"):
                            self._message_endpoint = data
                            logger.info(f"Discovered MCP message endpoint: {data}")
                            self._endpoint_ready.set()
                            continue

                        # JSON-RPC messages (HTTP+SSE or FastMCP)
                        try:
                            message = json.loads(data)
                            await self._message_queue.put(message)
                            # For HTTP+SSE, signal ready on first message
                            if self._protocol == self.PROTOCOL_HTTP_SSE:
                                self._endpoint_ready.set()
                        except json.JSONDecodeError:
                            continue

                    elif not line:
                        current_event = None

        except asyncio.CancelledError:
            pass
        except aiohttp.ClientError as e:
            logger.error(f"SSE connection error: {e}")
            self._connected = False
        finally:
            self._endpoint_ready.set()

    async def _streamable_sse_loop(self) -> None:
        """
        Background task for Streamable HTTP GET SSE stream.

        Per MCP spec (2025-11-25):
        - GET /mcp opens an SSE stream for server-to-client messages
        - Server can send requests and notifications
        - Client uses this for receiving server-initiated messages

        Note: This is optional - server may not support it (returns 405).
        POST responses still work for request/response patterns.
        """
        if self._sse_session is None:
            return

        import aiohttp
        import logging
        logger = logging.getLogger(__name__)

        headers = {"Accept": "text/event-stream"}
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id

        try:
            async with self._sse_session.get(
                f"{self.url}/mcp",
                headers=headers,
            ) as resp:
                if resp.status == 405:
                    # Server doesn't support standalone GET SSE - that's OK
                    logger.info("Server doesn't support GET SSE stream (405)")
                    return

                if resp.status != 200:
                    logger.warning(f"GET /mcp returned {resp.status}")
                    return

                # Parse SSE stream
                current_event = None
                async for line in resp.content:
                    line = line.decode("utf-8").strip()

                    if line.startswith("event:"):
                        current_event = line[6:].strip()
                    elif line.startswith("data:"):
                        data = line[5:].strip()
                        try:
                            message = json.loads(data)
                            await self._message_queue.put(message)
                        except json.JSONDecodeError:
                            continue
                    elif not line:
                        current_event = None

        except asyncio.CancelledError:
            pass
        except aiohttp.ClientError as e:
            # Connection errors are expected - SSE stream may close
            logger.debug(f"Streamable SSE stream ended: {e}")

    @property
    def is_connected(self) -> bool:
        """Check if session is active."""
        return self._connected and self._session is not None