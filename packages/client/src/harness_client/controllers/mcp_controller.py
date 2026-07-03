"""
MCP controller - proxy to AgentHarness MCP methods.

This controller wraps AgentHarness MCP APIs for UI convenience,
providing change notifications and UI-friendly data structures.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

# SDK imports
from harness import MCPServerConfig

logger = logging.getLogger(__name__)


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
    Controller for managing MCP server connections - proxies to AgentHarness.

    This is a thin wrapper around AgentHarness MCP methods,
    adding UI-specific features like change callbacks.
    """

    def __init__(self):
        # AgentHarness instance (set by set_agent)
        self._agent = None
        self._on_change: Callable | None = None
        # Local cache for UI display
        self._server_states: dict[str, MCPServerInfo] = {}

    def set_agent(self, agent) -> None:
        """
        Set the AgentHarness instance to proxy to.

        Args:
            agent: AgentHarness instance
        """
        self._agent = agent
        if self._on_change:
            self._on_change()

    def set_change_callback(self, callback: Callable[[], None]):
        """Set callback for server list changes."""
        self._on_change = callback

    def add_server_config(self, config: MCPServerConfig):
        """
        Add an MCP server configuration.

        Args:
            config: Server configuration
        """
        if not self._agent:
            # Store locally until agent is set
            self._server_states[config.name] = MCPServerInfo(
                name=config.name,
                transport=config.transport,
                status="未连接",
            )
            return

        # Add to agent's MCP manager
        self._agent._mcp_manager.add_server(config)
        self._server_states[config.name] = MCPServerInfo(
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
        if not self._agent:
            return False

        if name not in self._server_states:
            return False

        server_info = self._server_states[name]
        server_info.status = "连接中..."

        try:
            # Connect via agent
            await self._agent.add_mcp_server(name)

            # Update status
            tools = self._agent.get_mcp_server_tools(name)
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
        if not self._agent:
            return False

        try:
            await self._agent.disconnect_mcp_server(name)
            self._server_states[name].status = "未连接"
            self._server_states[name].tools_count = 0

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
        if name not in self._server_states:
            return False

        if self._agent:
            self._agent.remove_mcp_server(name)

        del self._server_states[name]
        if self._on_change:
            self._on_change()
        return True

    def update_server_config(self, old_name: str, new_config: dict) -> bool:
        """
        Update an MCP server configuration.

        Args:
            old_name: Current server name
            new_config: New configuration dict

        Returns:
            True if updated successfully
        """
        if old_name not in self._server_states:
            return False

        # Remove old and add new
        if self._agent:
            self._agent.remove_mcp_server(old_name)

            config = MCPServerConfig(
                name=new_config.get("name", old_name),
                transport=new_config.get("transport", "stdio"),
                command=new_config.get("command"),
                args=new_config.get("args", []),
                url=new_config.get("url"),
                timeout=new_config.get("timeout", 30),
            )
            self._agent._mcp_manager.add_server(config)

        # Update local tracking
        new_name = new_config.get("name", old_name)
        if old_name != new_name:
            del self._server_states[old_name]

        self._server_states[new_name] = MCPServerInfo(
            name=new_name,
            transport=new_config.get("transport", "stdio"),
            status="未连接",
        )

        if self._on_change:
            self._on_change()
        return True

    def get_all_tools(self) -> list:
        """
        Get all tools from connected servers.

        Returns:
            List of tool instances
        """
        if not self._agent:
            return []
        return self._agent.get_all_mcp_tools()

    def get_server_list(self) -> list[MCPServerInfo]:
        """Get list of all servers."""
        return list(self._server_states.values())

    def load_from_file(self, path: Path) -> int:
        """
        Load server configurations from file.

        Args:
            path: Path to config file (.mcp.json or .mcp.yaml)

        Returns:
            Number of servers loaded
        """
        if not self._agent:
            logger.warning("Agent not set, cannot load MCP config")
            return 0

        try:
            count = self._agent._mcp_manager.load_from_file(str(path))
            logger.info(f"MCPManager loaded {count} servers")

            # Update local tracking
            for config in self._agent._mcp_manager.list_server_configs():
                if config.name not in self._server_states:
                    self._server_states[config.name] = MCPServerInfo(
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
        if not self._agent:
            return

        import json

        config = {"mcpServers": {}}
        for name, _info in self._server_states.items():
            c = self._agent.get_mcp_server_config(name)
            if c:
                config["mcpServers"][name] = c.to_dict()

        path.write_text(json.dumps(config, indent=2, ensure_ascii=False))

    @property
    def servers(self) -> dict[str, MCPServerInfo]:
        """Get servers dict for backward compatibility."""
        return self._server_states

    @property
    def manager(self):
        """Get MCPManager for backward compatibility."""
        if self._agent:
            return self._agent._mcp_manager
        return None
