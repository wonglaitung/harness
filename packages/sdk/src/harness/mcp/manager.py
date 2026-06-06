"""
MCP Manager.

Manages multiple MCP server connections and integrates tools into Harness.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from harness.mcp.client import MCPClient, MCPServerInfo
from harness.mcp.transport import HTTPTransport, StdioTransport

if TYPE_CHECKING:
    from harness.mcp.tool_wrapper import MCPToolWrapper
    from harness.tools.base import ToolRegistry


@dataclass
class MCPServerConfig:
    """
    MCP server configuration.

    Defines how to connect to an MCP server.
    """

    name: str
    transport: str  # "stdio" or "http"
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    url: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    timeout: float = 30.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        result: Dict[str, Any] = {"transport": self.transport}

        if self.command:
            result["command"] = self.command
        if self.args:
            result["args"] = self.args
        if self.url:
            result["url"] = self.url
        if self.env:
            result["env"] = self.env
        if self.headers:
            result["headers"] = self.headers
        if not self.enabled:
            result["enabled"] = self.enabled

        return result

    @classmethod
    def from_dict(cls, name: str, config: Dict[str, Any]) -> "MCPServerConfig":
        """Create from dictionary format."""
        transport = config.get("transport", "stdio")

        # Support Claude Code format (defaults to stdio)
        if "command" in config:
            transport = "stdio"

        return cls(
            name=name,
            transport=transport,
            command=config.get("command"),
            args=config.get("args", []),
            url=config.get("url"),
            env=config.get("env", {}),
            headers=config.get("headers", {}),
            enabled=config.get("enabled", True),
            timeout=config.get("timeout", 30.0),
        )


# Default MCP config search paths (in priority order)
DEFAULT_MCP_CONFIG_PATHS = [
    "~/.harness/mcp.json",
    "~/.harness/mcp.yaml",
    ".agent/mcp.json",
    ".agent/mcp.yaml",
    ".mcp.json",
    ".mcp.yaml",
    "~/.claude/mcp.json",  # Claude Code compatibility
]


class MCPManager:
    """
    MCP server manager.

    Manages connections to multiple MCP servers and
    integrates their tools into the Harness tool registry.
    """

    def __init__(
        self,
        tool_registry: Optional["ToolRegistry"] = None,
        auto_load_configs: bool = True,
    ):
        """
        Initialize MCP manager.

        Args:
            tool_registry: Tool registry to register MCP tools
            auto_load_configs: Whether to auto-load config files
        """
        self.tool_registry = tool_registry
        self._clients: Dict[str, MCPClient] = {}
        self._configs: Dict[str, MCPServerConfig] = {}
        self._tool_wrappers: Dict[str, List["MCPToolWrapper"]] = {}

        if auto_load_configs:
            self._load_default_configs()

    def _load_default_configs(self) -> None:
        """Load MCP configs from default paths."""
        for config_path in DEFAULT_MCP_CONFIG_PATHS:
            path = Path(config_path)
            if not path.is_absolute():
                # Check in current directory
                cwd_path = Path.cwd() / config_path
                if cwd_path.exists():
                    self._load_config_file(cwd_path)
                    return

            # Check absolute paths (e.g., ~/.harness/mcp.json)
            expanded_path = path.expanduser()
            if expanded_path.exists():
                self._load_config_file(expanded_path)
                return

    def load_from_file(self, path: str | Path) -> int:
        """
        Load MCP configuration from a specific file.

        Args:
            path: Config file path (JSON or YAML)

        Returns:
            Number of servers loaded
        """
        config_path = Path(path)
        if not config_path.exists():
            return 0

        self._load_config_file(config_path)
        return len(self._configs)

    def _load_config_file(self, path: Path) -> None:
        """
        Load MCP configuration from file.

        Supports both JSON and YAML formats.

        Args:
            path: Config file path
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            content = path.read_text()
            logger.info(f"Loading MCP config from: {path}")
            logger.debug(f"Config content: {content[:500]}...")

            if path.suffix == ".json":
                config_data = json.loads(content)
            elif path.suffix in [".yaml", ".yml"]:
                try:
                    import yaml

                    config_data = yaml.safe_load(content)
                except ImportError:
                    # Skip YAML if not installed
                    logger.warning("YAML not installed, skipping YAML config")
                    return
            else:
                # Try JSON first, then YAML
                try:
                    config_data = json.loads(content)
                except json.JSONDecodeError:
                    try:
                        import yaml

                        config_data = yaml.safe_load(content)
                    except ImportError:
                        logger.warning("YAML not installed, skipping YAML config")
                        return

            # Parse mcpServers format (Claude Code compatible)
            servers = config_data.get("mcpServers", {})
            logger.info(f"Found {len(servers)} server(s) in config: {list(servers.keys())}")

            for name, server_config in servers.items():
                self.add_server(MCPServerConfig.from_dict(name, server_config))
                logger.info(f"Added server: {name}")

        except Exception as e:
            # Log config errors instead of silently ignoring
            logger.error(f"Error loading MCP config from {path}: {e}")
            pass

    def add_server(self, config: MCPServerConfig) -> None:
        """
        Add MCP server configuration.

        Args:
            config: Server configuration
        """
        self._configs[config.name] = config

    def remove_server(self, name: str) -> bool:
        """
        Remove MCP server configuration.

        Args:
            name: Server name

        Returns:
            True if server was removed
        """
        if name in self._configs:
            del self._configs[name]
            return True
        return False

    def get_server_config(self, name: str) -> Optional[MCPServerConfig]:
        """Get server configuration by name."""
        return self._configs.get(name)

    def list_server_configs(self) -> List[MCPServerConfig]:
        """List all server configurations."""
        return list(self._configs.values())

    async def connect_server(self, name: str) -> MCPClient:
        """
        Connect to a specific MCP server.

        Args:
            name: Server name

        Returns:
            Connected MCP client

        Raises:
            ValueError: If server config not found
            RuntimeError: If connection fails
        """
        if name in self._clients:
            return self._clients[name]

        config = self._configs.get(name)
        if not config:
            raise ValueError(f"Unknown MCP server: {name}")

        if not config.enabled:
            raise ValueError(f"MCP server {name} is disabled")

        # Create transport based on config
        if config.transport == "stdio":
            if not config.command:
                raise ValueError(f"Stdio transport requires command for {name}")
            transport = StdioTransport(
                command=config.command,
                args=config.args,
                env=config.env,
            )
        elif config.transport == "http":
            if not config.url:
                raise ValueError(f"HTTP transport requires url for {name}")
            transport = HTTPTransport(
                url=config.url,
                headers=config.headers,
                timeout=config.timeout,
            )
        else:
            raise ValueError(f"Unknown transport type: {config.transport}")

        # Create client and connect
        client = MCPClient(transport)
        await client.connect()

        # Register tools
        self._register_tools(name, client)

        self._clients[name] = client
        return client

    async def connect_all(self) -> Dict[str, MCPServerInfo]:
        """
        Connect to all enabled MCP servers.

        Returns:
            Dictionary of server name to server info
        """
        results: Dict[str, MCPServerInfo] = {}

        for name, config in self._configs.items():
            if not config.enabled:
                continue

            try:
                client = await self.connect_server(name)
                if client.server_info:
                    results[name] = client.server_info
            except Exception:
                # Continue with other servers on failure
                pass

        return results

    async def disconnect_server(self, name: str) -> bool:
        """
        Disconnect from a specific MCP server.

        Args:
            name: Server name

        Returns:
            True if server was disconnected
        """
        if name not in self._clients:
            return False

        client = self._clients.pop(name)
        await client.disconnect()

        # Unregister tools
        self._unregister_tools(name)

        return True

    async def disconnect_all(self) -> None:
        """Disconnect from all MCP servers."""
        for name in list(self._clients.keys()):
            await self.disconnect_server(name)

    def _register_tools(self, server_name: str, client: MCPClient) -> None:
        """
        Register MCP tools in tool registry.

        Args:
            server_name: Server name
            client: Connected MCP client
        """
        from harness.mcp.tool_wrapper import MCPToolWrapper

        wrappers: List[MCPToolWrapper] = []

        for mcp_tool in client.tools:
            wrapper = MCPToolWrapper(
                mcp_client=client,
                server_name=server_name,
                tool_name=mcp_tool.name,
                description=mcp_tool.description,
                input_schema=mcp_tool.input_schema,
            )

            # Register in tool registry if available
            if self.tool_registry:
                try:
                    self.tool_registry.register(wrapper, category="mcp")
                except ValueError:
                    # Tool name conflict, skip
                    pass

            wrappers.append(wrapper)

        self._tool_wrappers[server_name] = wrappers

    def _unregister_tools(self, server_name: str) -> None:
        """
        Unregister MCP tools from tool registry.

        Args:
            server_name: Server name
        """
        wrappers = self._tool_wrappers.pop(server_name, [])

        if self.tool_registry:
            for wrapper in wrappers:
                try:
                    self.tool_registry.unregister(wrapper.name)
                except KeyError:
                    pass

    def get_client(self, name: str) -> Optional[MCPClient]:
        """Get connected client by name."""
        return self._clients.get(name)

    def list_connected_servers(self) -> List[str]:
        """List connected server names."""
        return list(self._clients.keys())

    def get_server_tools(self, name: str) -> List["MCPToolWrapper"]:
        """Get tools from a specific server."""
        return self._tool_wrappers.get(name, [])

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """
        Directly call a tool on an MCP server.

        Args:
            server_name: Server name
            tool_name: Tool name (without server prefix)
            arguments: Tool arguments
            timeout: Timeout in seconds

        Returns:
            Tool result
        """
        client = self._clients.get(server_name)
        if not client:
            raise ValueError(f"Server not connected: {server_name}")

        return await client.call_tool(tool_name, arguments, timeout)

    @property
    def is_connected(self) -> bool:
        """Check if any server is connected."""
        return len(self._clients) > 0