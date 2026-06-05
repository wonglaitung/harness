"""
MCP controller - manages MCP server connections.
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

# SDK imports
from harness import MCPManager, MCPServerConfig


@dataclass
class MCPServerInfo:
    """Information about an MCP server."""

    name: str
    transport: str
    status: str = "未连接"  # 未连接, 已连接, 错误
    tools_count: int = 0
    error_message: str = ""


class MCPController:
    """
    Controller for managing MCP server connections.

    Features:
    - Add/remove MCP servers
    - Connect/disconnect servers
    - Get tools from connected servers
    - Load configuration from files
    """

    def __init__(self):
        self.manager = MCPManager()
        self.servers: dict[str, MCPServerInfo] = {}
        self._on_change: Callable | None = None

    def set_change_callback(self, callback: Callable[[], None]):
        """Set callback for server list changes."""
        self._on_change = callback

    def add_server_config(self, config: MCPServerConfig):
        """
        Add an MCP server configuration.

        Args:
            config: Server configuration
        """
        self.manager.add_server(config)
        self.servers[config.name] = MCPServerInfo(
            name=config.name,
            transport=config.transport,
            status="未连接",
        )
        if self._on_change:
            self._on_change()

    async def connect_server(self, name: str) -> bool:
        """
        Connect to an MCP server.

        Args:
            name: Server name

        Returns:
            True if connected successfully
        """
        if name not in self.servers:
            return False

        server_info = self.servers[name]
        server_info.status = "连接中..."

        try:
            # Connect via manager
            await self.manager.connect_server(name)

            # Update status
            tools = self.manager.get_server_tools(name)
            server_info.status = "已连接"
            server_info.tools_count = len(tools) if tools else 0
            server_info.error_message = ""

            if self._on_change:
                self._on_change()
            return True

        except Exception as e:
            server_info.status = "错误"
            server_info.error_message = str(e)
            if self._on_change:
                self._on_change()
            return False

    async def disconnect_server(self, name: str) -> bool:
        """
        Disconnect from an MCP server.

        Args:
            name: Server name

        Returns:
            True if disconnected successfully
        """
        if name not in self.servers:
            return False

        try:
            await self.manager.disconnect_server(name)
            self.servers[name].status = "未连接"
            self.servers[name].tools_count = 0

            if self._on_change:
                self._on_change()
            return True

        except Exception:
            return False

    def remove_server(self, name: str) -> bool:
        """
        Remove an MCP server configuration.

        Args:
            name: Server name

        Returns:
            True if removed successfully
        """
        if name not in self.servers:
            return False

        # TODO: Implement removal in manager
        del self.servers[name]
        if self._on_change:
            self._on_change()
        return True

    def get_all_tools(self) -> list:
        """
        Get all tools from connected servers.

        Returns:
            List of tool instances
        """
        tools = []
        for name, info in self.servers.items():
            if info.status == "已连接":
                server_tools = self.manager.get_server_tools(name)
                if server_tools:
                    tools.extend(server_tools)
        return tools

    def get_server_list(self) -> list[MCPServerInfo]:
        """Get list of all servers."""
        return list(self.servers.values())

    def load_from_file(self, path: Path) -> int:
        """
        Load server configurations from file.

        Args:
            path: Path to config file (.mcp.json or .mcp.yaml)

        Returns:
            Number of servers loaded
        """
        import logging
        logger = logging.getLogger(__name__)

        try:
            count = self.manager.load_from_file(str(path))
            logger.info(f"MCPManager loaded {count} servers")

            # Update local tracking
            for config in self.manager.list_server_configs():
                if config.name not in self.servers:
                    self.servers[config.name] = MCPServerInfo(
                        name=config.name,
                        transport=config.transport,
                        status="未连接",
                    )

            if self._on_change:
                self._on_change()
            return count

        except Exception as e:
            logger.error(f"Error loading MCP config: {e}")
            return 0

    def save_to_file(self, path: Path):
        """
        Save server configurations to file.

        Args:
            path: Path to save config file
        """
        import json

        config = {"mcpServers": {}}
        for name, _info in self.servers.items():
            # Get original config from manager
            for c in self.manager.list_server_configs():
                if c.name == name:
                    config["mcpServers"][name] = c.to_dict()
                    break

        path.write_text(json.dumps(config, indent=2, ensure_ascii=False))
