"""
MCP controller - proxy to AgentHarness MCP methods.

This controller wraps AgentHarness MCP APIs for UI convenience,
providing change notifications and UI-friendly data structures.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

# SDK imports
from harness import MCPServerConfig

if TYPE_CHECKING:
    from harness.mcp.client import MCPClient

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
        # Cache full configs before agent is available
        self._cached_configs: dict[str, MCPServerConfig] = {}
        # Standalone MCP clients (used before agent is available)
        self._standalone_clients: dict[str, "MCPClient"] = {}

    def set_agent(self, agent) -> None:
        """
        Set the AgentHarness instance to proxy to.

        Args:
            agent: AgentHarness instance
        """
        self._agent = agent
        # Note: MCP tools are already registered via chat_controller.initialize()
        # which gets tools from get_all_tools() and passes them to AgentHarness.
        # We just keep the standalone clients for tool execution.
        if self._on_change:
            self._on_change()

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
            # Store full config locally until agent is set
            self._cached_configs[config.name] = config
            self._server_states[config.name] = MCPServerInfo(
                name=config.name,
                transport=config.transport,
                status="未连接",
            )
            if self._on_change:
                self._on_change()
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
        if name not in self._server_states:
            return False

        server_info = self._server_states[name]
        server_info.status = "连接中..."

        logger.info(f"Connecting to MCP server: {name}")
        if self._on_change:
            self._on_change()

        try:
            if self._agent:
                # Connect via agent - need to get config and pass it
                config = self._cached_configs.get(name)
                if not config:
                    server_info.status = "错误"
                    server_info.error_message = "服务器配置未找到"
                    logger.error(f"MCP server {name}: config not found")
                    if self._on_change:
                        self._on_change()
                    return False

                # Build config dict for agent
                config_dict = {
                    "transport": config.transport,
                    "command": config.command,
                    "args": config.args,
                    "url": config.url,
                    "env": config.env,
                    "headers": config.headers,
                    "timeout": config.timeout,
                }
                logger.info(f"Connecting via agent with transport={config.transport}")
                await self._agent.add_mcp_server(name, config=config_dict)

                # Update status
                tools = self._agent.get_mcp_server_tools(name)
                server_info.status = "已连接"
                server_info.tools_count = len(tools) if tools else 0
                server_info.error_message = ""
                logger.info(f"MCP server {name} connected: {server_info.tools_count} tools")
            else:
                # Agent not available, use standalone MCPClient to test connection
                config = self._cached_configs.get(name)
                if not config:
                    server_info.status = "错误"
                    server_info.error_message = "服务器配置未找到"
                    logger.error(f"MCP server {name}: config not found")
                    if self._on_change:
                        self._on_change()
                    return False

                logger.info(f"Connecting via standalone client (agent not available)")
                # Use standalone client (similar to MCPServerDialog test)
                from harness.mcp.client import MCPClient
                from harness.mcp.transport import HTTPTransport, StdioTransport

                if config.transport == "stdio":
                    if not config.command:
                        raise ValueError("Stdio transport requires command")
                    transport = StdioTransport(
                        command=config.command,
                        args=config.args,
                        env=config.env,
                    )
                else:
                    if not config.url:
                        raise ValueError("HTTP transport requires URL")
                    transport = HTTPTransport(
                        url=config.url,
                        headers=config.headers,
                        timeout=config.timeout,
                    )

                client = MCPClient(transport)
                await client.connect()

                # Update status with discovered tools
                server_info.status = "已连接"
                server_info.tools_count = len(client.tools) if client.tools else 0
                server_info.error_message = ""
                logger.info(f"MCP server {name} connected via standalone client: {server_info.tools_count} tools")

                # Store client for later use (will be synced to agent when available)
                self._standalone_clients[name] = client

            if self._on_change:
                self._on_change()
            return True

        except Exception as e:
            server_info.status = "错误"
            server_info.error_message = str(e)
            logger.error(f"Failed to connect MCP server {name}: {e}")
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
        logger.info(f"Disconnecting MCP server: {name}")
        try:
            # Disconnect standalone client if exists
            if name in self._standalone_clients:
                client = self._standalone_clients[name]
                await client.disconnect()
                del self._standalone_clients[name]
                logger.info(f"Disconnected standalone client for {name}")

            # Disconnect via agent if available
            if self._agent:
                await self._agent.disconnect_mcp_server(name)
                logger.info(f"Disconnected via agent for {name}")

            if name in self._server_states:
                self._server_states[name].status = "未连接"
                self._server_states[name].tools_count = 0

            if self._on_change:
                self._on_change()
            logger.info(f"MCP server {name} disconnected successfully")
            return True

        except Exception as e:
            logger.error(f"Error disconnecting MCP server {name}: {e}")
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

        logger.info(f"Removing MCP server: {name}")
        if self._agent:
            self._agent.remove_mcp_server(name)

        # Remove from all caches
        if name in self._cached_configs:
            del self._cached_configs[name]
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

        # Create new config
        config = MCPServerConfig(
            name=new_config.get("name", old_name),
            transport=new_config.get("transport", "stdio"),
            command=new_config.get("command"),
            args=new_config.get("args", []),
            url=new_config.get("url"),
            env=new_config.get("env", {}),
            headers=new_config.get("headers", {}),
            enabled=new_config.get("enabled", True),
            timeout=new_config.get("timeout", 30),
        )

        # Remove old and add new in agent if available
        if self._agent:
            self._agent.remove_mcp_server(old_name)
            self._agent._mcp_manager.add_server(config)

        # Update cached configs
        if old_name in self._cached_configs:
            del self._cached_configs[old_name]
        self._cached_configs[config.name] = config

        # Update local tracking
        new_name = config.name
        if old_name != new_name:
            del self._server_states[old_name]

        self._server_states[new_name] = MCPServerInfo(
            name=new_name,
            transport=config.transport,
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
        tools = []

        # Get tools from standalone clients (before agent is available)
        for name, client in self._standalone_clients.items():
            for tool in client.tools:
                # Wrap MCP tool as Harness tool
                from harness.mcp.tool_wrapper import MCPToolWrapper
                wrapper = MCPToolWrapper(
                    mcp_client=client,
                    server_name=name,
                    tool_name=tool.name,
                    description=tool.description,
                    input_schema=tool.input_schema,
                )
                tools.append(wrapper)
            logger.debug(f"Got {len(client.tools)} tools from standalone client {name}")

        # Also get tools from agent if available
        if self._agent:
            agent_tools = self._agent.get_all_mcp_tools()
            tools.extend(agent_tools)
            if agent_tools:
                logger.debug(f"Got {len(agent_tools)} tools from agent")

        if tools:
            logger.info(f"get_all_tools: returning {len(tools)} tools from {len(self._standalone_clients)} standalone + agent")
        return tools

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
        import json

        try:
            # Read config file directly
            config_path = Path(path)
            if not config_path.exists():
                logger.warning(f"MCP config file not found: {path}")
                return 0

            config_data = json.loads(config_path.read_text(encoding="utf-8"))
            servers = config_data.get("mcpServers", {})
            count = 0

            for name, server_config in servers.items():
                # Create MCPServerConfig
                config = MCPServerConfig(
                    name=name,
                    transport=server_config.get("transport", "stdio"),
                    command=server_config.get("command"),
                    args=server_config.get("args", []),
                    url=server_config.get("url"),
                    env=server_config.get("env", {}),
                    headers=server_config.get("headers", {}),
                    enabled=server_config.get("enabled", True),
                    timeout=server_config.get("timeout", 30.0),
                )

                # Cache full config for later sync to SDK
                self._cached_configs[config.name] = config

                # Add to agent's manager if available
                if self._agent:
                    self._agent._mcp_manager.add_server(config)

                # Update local tracking
                self._server_states[config.name] = MCPServerInfo(
                    name=config.name,
                    transport=config.transport,
                    status="未连接",
                )
                count += 1

            logger.info(f"Loaded {count} MCP server configs from {path}")

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

        # Use cached configs first (populated before agent was available)
        for name, cached_config in self._cached_configs.items():
            config["mcpServers"][name] = cached_config.to_dict()

        # Then add configs from agent's manager (for servers added after agent was set)
        if self._agent:
            for name in self._server_states:
                if name not in config["mcpServers"]:
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

    def list_server_configs(self) -> list:
        """
        List all server configurations.

        Returns configurations from cached configs if agent not available,
        otherwise from agent's manager.

        Returns:
            List of MCPServerConfig objects
        """
        if self._agent and self._agent._mcp_manager:
            return self._agent._mcp_manager.list_server_configs()

        # Return cached configs (populated before agent was available)
        return list(self._cached_configs.values())

    def get_server_config(self, name: str):
        """
        Get configuration for a specific server.

        Args:
            name: Server name

        Returns:
            MCPServerConfig or None
        """
        # First check cached configs (populated before agent was available)
        if name in self._cached_configs:
            return self._cached_configs[name]

        # Then check agent's MCP manager
        if self._agent:
            return self._agent.get_mcp_server_config(name)

        return None
