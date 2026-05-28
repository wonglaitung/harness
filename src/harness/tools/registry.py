"""
Tool registry for managing available tools.
"""

from dataclasses import dataclass
from typing import Any

from harness.tools.base import Tool


@dataclass
class ToolInfo:
    """Information about a registered tool."""
    tool: Tool
    category: str = "custom"
    enabled: bool = True


class ToolRegistry:
    """
    Registry for managing available tools.

    Tools are registered with a unique name and can be retrieved,
    enabled/disabled, or listed by category.
    """

    def __init__(self):
        self._tools: dict[str, ToolInfo] = {}

    def register(
        self,
        tool: Tool,
        category: str = "custom",
    ) -> None:
        """
        Register a tool.

        Args:
            tool: Tool instance to register
            category: Category for organization
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")

        self._tools[tool.name] = ToolInfo(
            tool=tool,
            category=category,
            enabled=True,
        )

    def unregister(self, name: str) -> Tool | None:
        """
        Unregister a tool.

        Args:
            name: Tool name to unregister

        Returns:
            The unregistered tool, or None if not found
        """
        if name in self._tools:
            info = self._tools.pop(name)
            return info.tool
        return None

    def get(self, name: str) -> Tool | None:
        """
        Get a tool by name.

        Args:
            name: Tool name

        Returns:
            Tool instance or None
        """
        info = self._tools.get(name)
        return info.tool if info and info.enabled else None

    def get_all(self, enabled_only: bool = True) -> list[Tool]:
        """
        Get all registered tools.

        Args:
            enabled_only: Only return enabled tools

        Returns:
            List of tool instances
        """
        return [
            info.tool
            for info in self._tools.values()
            if not enabled_only or info.enabled
        ]

    def get_definitions(self) -> list[dict[str, Any]]:
        """
        Get tool definitions for LLM API.

        Returns:
            List of tool definitions
        """
        return [
            tool.to_definition()
            for tool in self.get_all(enabled_only=True)
        ]

    def enable(self, name: str) -> bool:
        """Enable a tool."""
        if name in self._tools:
            self._tools[name].enabled = True
            return True
        return False

    def disable(self, name: str) -> bool:
        """Disable a tool."""
        if name in self._tools:
            self._tools[name].enabled = False
            return True
        return False

    def list_tools(self) -> dict[str, dict[str, Any]]:
        """
        List all tools with their status.

        Returns:
            Dict mapping tool names to info
        """
        return {
            name: {
                "description": info.tool.description,
                "category": info.category,
                "enabled": info.enabled,
            }
            for name, info in self._tools.items()
        }

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)

    def __iter__(self):
        return iter(self.get_all())
