"""
MCP Client.

Implements JSON-RPC 2.0 protocol for MCP server communication.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from harness.mcp.transport import MCPTransport

logger = logging.getLogger(__name__)


@dataclass
class MCPTool:
    """
    MCP tool definition.

    Represents a tool exposed by an MCP server.
    """

    name: str
    description: str
    input_schema: Dict[str, Any]


@dataclass
class MCPServerInfo:
    """
    MCP server information.

    Contains metadata about the connected server.
    """

    name: str
    version: str
    capabilities: List[str] = field(default_factory=list)


class MCPClient:
    """
    MCP client implementing JSON-RPC 2.0.

    Handles connection initialization, tool discovery,
    and tool execution via MCP protocol.
    """

    def __init__(
        self,
        transport: "MCPTransport",
        client_name: str = "harness",
        client_version: str = "1.0.0",
    ):
        """
        Initialize MCP client.

        Args:
            transport: Transport layer for communication
            client_name: Client name sent during initialization
            client_version: Client version sent during initialization
        """
        self.transport = transport
        self.client_name = client_name
        self.client_version = client_version

        self._server_info: Optional[MCPServerInfo] = None
        self._tools: List[MCPTool] = []
        self._resources: List[Dict[str, Any]] = []
        self._request_handlers: Dict[str, asyncio.Future[Dict[str, Any]]] = {}
        self._message_task: Optional[asyncio.Task] = None
        self._connected = False

    async def connect(self) -> MCPServerInfo:
        """
        Connect to MCP server and initialize.

        Returns:
            Server information after successful initialization
        """
        if self._connected:
            logger.debug(f"[MCPClient] Already connected to {self._server_info.name if self._server_info else 'unknown'}")
            return self._server_info

        logger.info(f"[MCPClient] Starting connection process...")
        logger.debug(f"[MCPClient] Transport type: {type(self.transport).__name__}")

        # Connect transport
        logger.info(f"[MCPClient] Connecting transport...")
        try:
            await self.transport.connect()
            logger.info(f"[MCPClient] Transport connected successfully")
        except Exception as e:
            logger.error(f"[MCPClient] Transport connection failed: {e}")
            raise

        # Start message handling loop
        logger.debug(f"[MCPClient] Starting message loop task")
        self._message_task = asyncio.create_task(self._message_loop())

        # Send initialize request
        try:
            logger.info(f"[MCPClient] Sending initialize request...")
            init_params = {
                "protocolVersion": "2024-11-05",
                "clientInfo": {
                    "name": self.client_name,
                    "version": self.client_version,
                },
                "capabilities": {
                    "tools": {},
                    "resources": {},
                },
            }
            logger.debug(f"[MCPClient] Initialize params: {init_params}")

            response = await self._request(
                "initialize",
                init_params,
                timeout=30.0,  # Increased timeout for npm-based servers that may need to download packages
            )
            logger.info(f"[MCPClient] Initialize response received")
            logger.debug(f"[MCPClient] Initialize response: {response}")

            # Parse server info
            server_info = response.get("serverInfo", {})
            self._server_info = MCPServerInfo(
                name=server_info.get("name", "unknown"),
                version=server_info.get("version", "0.0.0"),
                capabilities=list(response.get("capabilities", {}).keys()),
            )
            logger.info(f"[MCPClient] Server: {self._server_info.name} v{self._server_info.version}")
            logger.debug(f"[MCPClient] Capabilities: {self._server_info.capabilities}")

            # Send initialized notification
            logger.debug(f"[MCPClient] Sending initialized notification")
            await self._notify("notifications/initialized", {})

            # Discover tools and resources
            logger.info(f"[MCPClient] Discovering tools...")
            await self._discover_tools()
            logger.info(f"[MCPClient] Discovering resources...")
            await self._discover_resources()

            self._connected = True
            logger.info(f"[MCPClient] Connection complete: {len(self._tools)} tools, {len(self._resources)} resources")
            return self._server_info

        except Exception as e:
            # Clean up on failure
            logger.error(f"[MCPClient] Failed to connect to MCP server: {e}")
            logger.error(f"[MCPClient] Exception type: {type(e).__name__}")
            # Check stderr for more info
            if hasattr(self.transport, 'check_stderr'):
                logger.debug(f"[MCPClient] Checking stderr for more info...")
                stderr = await self.transport.check_stderr()
                if stderr:
                    logger.error(f"[MCPClient] MCP server stderr: {stderr}")
            if self._message_task:
                self._message_task.cancel()
            await self.transport.disconnect()
            raise RuntimeError(f"Failed to connect to MCP server: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from MCP server."""
        logger.info(f"Disconnecting from MCP server: {self._server_info.name if self._server_info else 'unknown'}")
        self._connected = False

        if self._message_task:
            self._message_task.cancel()
            try:
                await self._message_task
            except asyncio.CancelledError:
                pass
            self._message_task = None

        # Cancel pending requests
        for future in self._request_handlers.values():
            if not future.done():
                future.cancel()
        self._request_handlers.clear()

        await self.transport.disconnect()
        logger.info("MCP server disconnected")

    async def _discover_tools(self) -> None:
        """Discover available tools from server."""
        try:
            response = await self._request("tools/list", {}, timeout=5.0)
            tools = response.get("tools", [])

            self._tools = [
                MCPTool(
                    name=tool.get("name", ""),
                    description=tool.get("description", ""),
                    input_schema=tool.get("inputSchema", {}),
                )
                for tool in tools
            ]
            logger.info(f"Discovered {len(self._tools)} tools: {[t.name for t in self._tools]}")
        except Exception as e:
            # Server may not support tools
            logger.warning(f"Failed to discover tools: {e}")
            self._tools = []

    async def _discover_resources(self) -> None:
        """Discover available resources from server."""
        try:
            response = await self._request("resources/list", {}, timeout=5.0)
            self._resources = response.get("resources", [])
            logger.info(f"Discovered {len(self._resources)} resources")
        except Exception as e:
            # Server may not support resources
            logger.debug(f"Failed to discover resources: {e}")
            self._resources = []

    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """
        Call a tool on the MCP server.

        Args:
            name: Tool name
            arguments: Tool arguments
            timeout: Timeout in seconds

        Returns:
            Tool execution result with content and error status
        """
        if not self._connected:
            raise RuntimeError("Client not connected")

        logger.info(f"Calling MCP tool: {name} with args: {list(arguments.keys())}")

        response = await self._request(
            "tools/call",
            {
                "name": name,
                "arguments": arguments,
            },
            timeout=timeout,
        )

        # Parse response content
        content_items = response.get("content", [])
        is_error = response.get("isError", False)

        # Extract text content
        text_content = "\n".join(
            item.get("text", "")
            for item in content_items
            if item.get("type") == "text"
        )

        result_len = len(text_content) if text_content else 0
        logger.info(f"MCP tool {name} returned: error={is_error}, content_len={result_len}")

        return {
            "content": text_content,
            "is_error": is_error,
            "raw_content": content_items,
        }

    async def read_resource(
        self,
        uri: str,
        timeout: float = 10.0,
    ) -> Dict[str, Any]:
        """
        Read a resource from the MCP server.

        Args:
            uri: Resource URI
            timeout: Timeout in seconds

        Returns:
            Resource content
        """
        if not self._connected:
            raise RuntimeError("Client not connected")

        response = await self._request(
            "resources/read",
            {"uri": uri},
            timeout=timeout,
        )

        return response

    async def _request(
        self,
        method: str,
        params: Dict[str, Any],
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """
        Send JSON-RPC request.

        Args:
            method: RPC method name
            params: Method parameters
            timeout: Timeout in seconds

        Returns:
            Response result
        """
        request_id = str(uuid.uuid4())
        future: asyncio.Future[Dict[str, Any]] = asyncio.Future()
        self._request_handlers[request_id] = future

        # Send request
        await self.transport.send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            }
        )

        # Wait for response
        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            self._request_handlers.pop(request_id, None)
            raise asyncio.TimeoutError(f"Request {method} timed out")
        finally:
            self._request_handlers.pop(request_id, None)

    async def _notify(
        self,
        method: str,
        params: Dict[str, Any],
    ) -> None:
        """
        Send JSON-RPC notification (no response expected).

        Args:
            method: RPC method name
            params: Method parameters
        """
        await self.transport.send(
            {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
            }
        )

    async def _message_loop(self) -> None:
        """Handle incoming messages from server."""
        try:
            async for message in self.transport.receive():
                # Handle response to our request
                if "id" in message:
                    request_id = message["id"]
                    if request_id in self._request_handlers:
                        future = self._request_handlers.pop(request_id)

                        if "error" in message:
                            error = message.get("error", {})
                            error_msg = error.get("message", "Unknown error")
                            if not future.done():
                                future.set_exception(
                                    RuntimeError(error_msg)
                                )
                        else:
                            if not future.done():
                                future.set_result(
                                    message.get("result", {})
                                )

                # Handle server notifications
                elif "method" in message:
                    # Could handle tool list changes, etc.
                    pass

        except asyncio.CancelledError:
            pass
        except Exception:
            self._connected = False

    @property
    def server_info(self) -> Optional[MCPServerInfo]:
        """Get server information."""
        return self._server_info

    @property
    def tools(self) -> List[MCPTool]:
        """Get available tools."""
        return self._tools

    @property
    def resources(self) -> List[Dict[str, Any]]:
        """Get available resources."""
        return self._resources

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._connected