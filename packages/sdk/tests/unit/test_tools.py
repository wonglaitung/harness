"""Tests for tool system."""

import pytest
from pathlib import Path

from harness.tools.base import Tool, ToolContext
from harness.tools.registry import ToolRegistry
from harness.tools.permissions import PermissionSet
from harness.tools.builtins import ReadTool, WriteTool, GlobTool
from harness.types import ToolResult


class TestToolRegistry:
    """Tests for ToolRegistry."""

    def test_register_tool(self):
        """Test registering a tool."""
        registry = ToolRegistry()
        tool = ReadTool()
        registry.register(tool)

        assert "read" in registry
        assert registry.get("read") == tool

    def test_duplicate_register_raises(self):
        """Test that duplicate registration raises."""
        registry = ToolRegistry()
        tool = ReadTool()
        registry.register(tool)

        with pytest.raises(ValueError):
            registry.register(tool)

    def test_unregister_tool(self):
        """Test unregistering a tool."""
        registry = ToolRegistry()
        tool = ReadTool()
        registry.register(tool)

        removed = registry.unregister("read")
        assert removed == tool
        assert "read" not in registry

    def test_enable_disable(self):
        """Test enabling and disabling tools."""
        registry = ToolRegistry()
        registry.register(ReadTool())

        registry.disable("read")
        assert registry.get("read") is None

        registry.enable("read")
        assert registry.get("read") is not None

    def test_get_definitions(self):
        """Test getting tool definitions."""
        registry = ToolRegistry()
        registry.register(ReadTool())
        registry.register(WriteTool())

        defs = registry.get_definitions()
        assert len(defs) == 2
        assert any(d["name"] == "read" for d in defs)
        assert any(d["name"] == "write" for d in defs)


class TestPermissionSet:
    """Tests for PermissionSet."""

    def test_full_access(self):
        """Test full access permission set."""
        perm = PermissionSet.full_access()
        assert perm.network_enabled

    def test_read_only(self):
        """Test read-only permission set."""
        perm = PermissionSet.read_only(["/tmp"])
        assert perm.is_path_allowed("/tmp/file.txt", "read")
        assert not perm.is_path_allowed("/tmp/file.txt", "write")

    def test_sandbox(self):
        """Test sandbox permission set."""
        perm = PermissionSet.sandbox("/workspace")
        assert perm.is_path_allowed("/workspace/file.txt", "read")
        assert perm.is_path_allowed("/workspace/file.txt", "write")
        assert not perm.is_path_allowed("/etc/passwd", "read")

    def test_command_blocking(self):
        """Test command blocking."""
        perm = PermissionSet()
        perm.blocked_commands.add("rm")

        assert not perm.is_command_allowed("rm -rf /")
        assert perm.is_command_allowed("ls")


class TestReadTool:
    """Tests for ReadTool."""

    @pytest.mark.asyncio
    async def test_read_existing_file(self, temp_workspace):
        """Test reading an existing file."""
        # Create test file
        test_file = temp_workspace / "test.txt"
        test_file.write_text("Hello, World!")

        tool = ReadTool()
        context = ToolContext(
            session_id="test",
            working_directory=temp_workspace,
            permissions=PermissionSet.full_access(),
        )

        result = await tool.execute(
            {"file_path": str(test_file)},
            context,
        )

        assert result.success
        assert "Hello, World!" in result.content

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, temp_workspace):
        """Test reading a nonexistent file."""
        tool = ReadTool()
        context = ToolContext(
            session_id="test",
            working_directory=temp_workspace,
            permissions=PermissionSet.full_access(),
        )

        result = await tool.execute(
            {"file_path": "nonexistent.txt"},
            context,
        )

        assert not result.success
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_read_with_offset_limit(self, temp_workspace):
        """Test reading with offset and limit."""
        test_file = temp_workspace / "lines.txt"
        test_file.write_text("line1\nline2\nline3\nline4\nline5")

        tool = ReadTool()
        context = ToolContext(
            session_id="test",
            working_directory=temp_workspace,
            permissions=PermissionSet.full_access(),
        )

        result = await tool.execute(
            {"file_path": str(test_file), "offset": 1, "limit": 2},
            context,
        )

        assert result.success
        assert "line2" in result.content
        assert "line3" in result.content
        assert "line1" not in result.content


class TestWriteTool:
    """Tests for WriteTool."""

    @pytest.mark.asyncio
    async def test_write_new_file(self, temp_workspace):
        """Test writing a new file."""
        tool = WriteTool()
        context = ToolContext(
            session_id="test",
            working_directory=temp_workspace,
            permissions=PermissionSet.full_access(),
        )

        result = await tool.execute(
            {"file_path": "new.txt", "content": "New content"},
            context,
        )

        assert result.success
        assert (temp_workspace / "new.txt").exists()
        assert (temp_workspace / "new.txt").read_text() == "New content"

    @pytest.mark.asyncio
    async def test_write_creates_directories(self, temp_workspace):
        """Test that write creates parent directories."""
        tool = WriteTool()
        context = ToolContext(
            session_id="test",
            working_directory=temp_workspace,
            permissions=PermissionSet.full_access(),
        )

        result = await tool.execute(
            {"file_path": "sub/dir/file.txt", "content": "content"},
            context,
        )

        assert result.success
        assert (temp_workspace / "sub" / "dir" / "file.txt").exists()


class TestGlobTool:
    """Tests for GlobTool."""

    @pytest.mark.asyncio
    async def test_find_files(self, temp_workspace):
        """Test finding files with glob pattern."""
        # Create some files
        (temp_workspace / "file1.txt").touch()
        (temp_workspace / "file2.txt").touch()
        (temp_workspace / "file3.py").touch()

        tool = GlobTool()
        context = ToolContext(
            session_id="test",
            working_directory=temp_workspace,
            permissions=PermissionSet.full_access(),
        )

        result = await tool.execute(
            {"pattern": "*.txt"},
            context,
        )

        assert result.success
        assert "file1.txt" in result.content
        assert "file2.txt" in result.content
        assert "file3.py" not in result.content