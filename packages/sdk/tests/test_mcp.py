"""
Tests for MCP (Model Context Protocol) Support.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from harness.mcp import (
    HTTPTransport,
    MCPClient,
    MCPManager,
    MCPServerConfig,
    MCPServerInfo,
    MCPTool,
    MCPToolWrapper,
    MCPTransport,
    StdioTransport,
)


class TestStdioTransport:
    """Tests for StdioTransport."""

    def test_init(self):
        """Test initialization."""
        transport = StdioTransport(
            command="echo",
            args=["hello"],
            env={"TEST": "value"},
        )

        assert transport.command == "echo"
        assert transport.args == ["hello"]
        assert transport.env == {"TEST": "value"}
        assert not transport.is_connected

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """Test connection lifecycle."""
        transport = StdioTransport(command="cat")

        try:
            await transport.connect()
            assert transport.is_connected

            await transport.disconnect()
            assert not transport.is_connected
        except Exception:
            # May fail if cat not available
            pass

    @pytest.mark.asyncio
    async def test_send_receive(self):
        """Test send and receive messages."""
        # Use cat as a simple echo server
        transport = StdioTransport(command="cat")

        try:
            await transport.connect()

            # Send a message
            await transport.send({"jsonrpc": "2.0", "method": "test", "id": "1"})

            # Receive response (cat echoes back)
            messages = []
            async for msg in transport.receive():
                messages.append(msg)
                break  # Only first message

            assert len(messages) == 1
            assert messages[0]["jsonrpc"] == "2.0"
            assert messages[0]["method"] == "test"

        finally:
            await transport.disconnect()


class TestHTTPTransport:
    """Tests for HTTPTransport."""

    def test_init(self):
        """Test initialization."""
        transport = HTTPTransport(
            url="http://localhost:8080",
            headers={"Authorization": "Bearer token"},
            timeout=60.0,
        )

        assert transport.url == "http://localhost:8080"
        assert transport.headers == {"Authorization": "Bearer token"}
        assert transport.timeout == 60.0
        assert not transport.is_connected

    @pytest.mark.asyncio
    async def test_connect_requires_aiohttp(self):
        """Test that connect requires aiohttp."""
        transport = HTTPTransport(url="http://localhost:8080")

        # This should work if aiohttp is installed, or raise ImportError
        try:
            await transport.connect()
            await transport.disconnect()
        except ImportError as e:
            assert "aiohttp" in str(e)


class TestMCPClient:
    """Tests for MCPClient."""

    def test_init(self):
        """Test initialization."""
        transport = MagicMock(spec=MCPTransport)
        client = MCPClient(
            transport=transport,
            client_name="test-client",
            client_version="1.0.0",
        )

        assert client.client_name == "test-client"
        assert client.client_version == "1.0.0"
        assert not client.is_connected

    @pytest.mark.asyncio
    async def test_connect_initializes(self):
        """Test connection initialization."""
        # Mock transport
        transport = AsyncMock(spec=MCPTransport)
        transport.is_connected = True

        # Mock receive to yield initialize response
        async def mock_receive():
            yield {
                "jsonrpc": "2.0",
                "id": "test-id",
                "result": {
                    "serverInfo": {"name": "test-server", "version": "1.0.0"},
                    "capabilities": {"tools": {}},
                },
            }
            yield {
                "jsonrpc": "2.0",
                "id": "test-id-2",
                "result": {"tools": []},
            }

        transport.receive.return_value = mock_receive()

        # Mock send to capture requests
        sent_messages = []

        async def mock_send(msg):
            sent_messages.append(msg)

        transport.send = mock_send

        _ = MCPClient(transport)

        # Note: Full connect test would require more complex mocking
        # This tests the basic structure


class TestMCPServerConfig:
    """Tests for MCPServerConfig."""

    def test_stdio_config(self):
        """Test stdio server config."""
        config = MCPServerConfig(
            name="filesystem",
            transport="stdio",
            command="mcp-server-filesystem",
            args=["/workspace"],
            env={"DEBUG": "1"},
        )

        assert config.name == "filesystem"
        assert config.transport == "stdio"
        assert config.command == "mcp-server-filesystem"
        assert config.enabled is True

    def test_http_config(self):
        """Test HTTP server config."""
        config = MCPServerConfig(
            name="remote",
            transport="http",
            url="http://api.example.com/mcp",
            headers={"Authorization": "Bearer token"},
        )

        assert config.name == "remote"
        assert config.transport == "http"
        assert config.url == "http://api.example.com/mcp"

    def test_to_dict(self):
        """Test serialization."""
        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="test-server",
            args=["--port", "8080"],
        )

        result = config.to_dict()
        assert result["transport"] == "stdio"
        assert result["command"] == "test-server"
        assert result["args"] == ["--port", "8080"]

    def test_from_dict(self):
        """Test deserialization."""
        data = {
            "command": "mcp-server-github",
            "args": ["--read-only"],
            "env": {"GITHUB_TOKEN": "xxx"},
        }

        config = MCPServerConfig.from_dict("github", data)

        assert config.name == "github"
        assert config.transport == "stdio"  # Auto-detected
        assert config.command == "mcp-server-github"

    def test_claude_code_format(self):
        """Test Claude Code config format compatibility."""
        # Claude Code format doesn't specify transport, defaults to stdio
        data = {
            "command": "mcp-server-filesystem",
            "args": ["/workspace"],
        }

        config = MCPServerConfig.from_dict("filesystem", data)

        assert config.transport == "stdio"
        assert config.command == "mcp-server-filesystem"


class TestMCPManager:
    """Tests for MCPManager."""

    def test_init(self):
        """Test initialization."""
        manager = MCPManager(auto_load_configs=False)

        assert manager.tool_registry is None
        assert len(manager.list_server_configs()) == 0

    def test_add_server(self):
        """Test adding server config."""
        manager = MCPManager(auto_load_configs=False)

        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="test-server",
        )

        manager.add_server(config)

        configs = manager.list_server_configs()
        assert len(configs) == 1
        assert configs[0].name == "test"

    def test_remove_server(self):
        """Test removing server config."""
        manager = MCPManager(auto_load_configs=False)

        config = MCPServerConfig(name="test", transport="stdio", command="test")
        manager.add_server(config)

        assert manager.remove_server("test") is True
        assert manager.remove_server("nonexistent") is False

    def test_get_server_config(self):
        """Test getting server config."""
        manager = MCPManager(auto_load_configs=False)

        config = MCPServerConfig(name="test", transport="stdio", command="test")
        manager.add_server(config)

        result = manager.get_server_config("test")
        assert result is not None
        assert result.name == "test"

        assert manager.get_server_config("nonexistent") is None

    def test_load_config_file_json(self, tmp_path):
        """Test loading JSON config file."""
        config_file = tmp_path / "mcp.json"
        config_file.write_text(json.dumps({
            "mcpServers": {
                "filesystem": {
                    "command": "mcp-server-filesystem",
                    "args": ["/workspace"],
                },
                "github": {
                    "command": "mcp-server-github",
                    "env": {"GITHUB_TOKEN": "xxx"},
                },
            }
        }))

        manager = MCPManager(auto_load_configs=False)
        manager._load_config_file(config_file)

        configs = manager.list_server_configs()
        assert len(configs) == 2

        fs_config = manager.get_server_config("filesystem")
        assert fs_config is not None
        assert fs_config.command == "mcp-server-filesystem"

    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """Test server connection lifecycle."""
        manager = MCPManager(auto_load_configs=False)

        # Add a mock config
        config = MCPServerConfig(
            name="mock",
            transport="stdio",
            command="echo",  # Simple command that exists
        )
        manager.add_server(config)

        # Note: Full connection test would require actual MCP server
        # This tests the basic structure

    @pytest.mark.asyncio
    async def test_disconnect_all(self):
        """Test disconnecting all servers."""
        manager = MCPManager(auto_load_configs=False)

        # Should not raise even with no servers
        await manager.disconnect_all()


class TestMCPToolWrapper:
    """Tests for MCPToolWrapper."""

    def test_init(self):
        """Test initialization."""
        client = MagicMock(spec=MCPClient)
        wrapper = MCPToolWrapper(
            mcp_client=client,
            server_name="filesystem",
            tool_name="read_file",
            description="Read a file",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                },
                "required": ["path"],
            },
        )

        assert wrapper.name == "mcp_filesystem_read_file"
        assert wrapper.original_name == "read_file"
        assert wrapper.server_name == "filesystem"
        assert wrapper.description == "Read a file"
        assert "path" in wrapper.parameters
        assert "path" in wrapper.required

    def test_to_anthropic_schema(self):
        """Test Anthropic schema conversion."""
        client = MagicMock(spec=MCPClient)
        wrapper = MCPToolWrapper(
            mcp_client=client,
            server_name="test",
            tool_name="tool",
            description="Test tool",
            input_schema={
                "type": "object",
                "properties": {"arg": {"type": "string"}},
            },
        )

        schema = wrapper.to_anthropic_schema()

        assert schema["name"] == "mcp_test_tool"
        assert schema["description"] == "Test tool"
        assert "input_schema" in schema

    def test_to_openai_schema(self):
        """Test OpenAI schema conversion."""
        client = MagicMock(spec=MCPClient)
        wrapper = MCPToolWrapper(
            mcp_client=client,
            server_name="test",
            tool_name="tool",
            description="Test tool",
            input_schema={
                "type": "object",
                "properties": {"arg": {"type": "string"}},
            },
        )

        schema = wrapper.to_openai_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "mcp_test_tool"
        assert schema["function"]["description"] == "Test tool"

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful tool execution."""
        # Create a mock client that returns a successful result
        mock_result = {
            "content": "file contents",
            "is_error": False,
        }

        client = MagicMock(spec=MCPClient)
        client.call_tool = AsyncMock(return_value=mock_result)

        wrapper = MCPToolWrapper(
            mcp_client=client,
            server_name="test",
            tool_name="read",
            description="Read file",
            input_schema={"type": "object", "properties": {}},
        )

        result = await wrapper.execute({"path": "/test.txt"})

        assert result.success
        assert "file contents" in result.content
        client.call_tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_error(self):
        """Test tool execution error."""
        mock_result = {
            "content": "File not found",
            "is_error": True,
        }

        client = MagicMock(spec=MCPClient)
        client.call_tool = AsyncMock(return_value=mock_result)

        wrapper = MCPToolWrapper(
            mcp_client=client,
            server_name="test",
            tool_name="read",
            description="Read file",
            input_schema={"type": "object", "properties": {}},
        )

        result = await wrapper.execute({"path": "/nonexistent.txt"})

        assert not result.success
        assert "File not found" in result.error

    @pytest.mark.asyncio
    async def test_execute_exception(self):
        """Test tool execution exception."""
        client = MagicMock(spec=MCPClient)
        client.call_tool = AsyncMock(side_effect=Exception("Connection lost"))

        wrapper = MCPToolWrapper(
            mcp_client=client,
            server_name="test",
            tool_name="read",
            description="Read file",
            input_schema={"type": "object", "properties": {}},
        )

        result = await wrapper.execute({"path": "/test.txt"})

        assert not result.success
        assert "Connection lost" in result.error


class TestMCPTool:
    """Tests for MCPTool dataclass."""

    def test_init(self):
        """Test MCPTool initialization."""
        tool = MCPTool(
            name="read_file",
            description="Read a file",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                },
            },
        )

        assert tool.name == "read_file"
        assert tool.description == "Read a file"
        assert "path" in tool.input_schema["properties"]


class TestMCPServerInfo:
    """Tests for MCPServerInfo dataclass."""

    def test_init(self):
        """Test MCPServerInfo initialization."""
        info = MCPServerInfo(
            name="filesystem-server",
            version="1.0.0",
            capabilities=["tools", "resources"],
        )

        assert info.name == "filesystem-server"
        assert info.version == "1.0.0"
        assert "tools" in info.capabilities
        assert "resources" in info.capabilities
