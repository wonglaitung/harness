"""
MCP (Model Context Protocol) Support.

Provides integration with external MCP servers for tool extension.
"""

from harness.mcp.transport import (
    HTTPTransport,
    MCPTransport,
    StdioTransport,
)
from harness.mcp.client import (
    MCPClient,
    MCPServerInfo,
    MCPTool,
)
from harness.mcp.manager import (
    MCPManager,
    MCPServerConfig,
)
from harness.mcp.tool_wrapper import MCPToolWrapper

__all__ = [
    # Transport
    "MCPTransport",
    "StdioTransport",
    "HTTPTransport",
    # Client
    "MCPClient",
    "MCPTool",
    "MCPServerInfo",
    # Manager
    "MCPManager",
    "MCPServerConfig",
    # Tool Wrapper
    "MCPToolWrapper",
]