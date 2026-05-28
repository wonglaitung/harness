"""
Base Tool interface and context.

Defines the abstract interface for all tools in the Harness framework.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from harness.types import ToolResult

if TYPE_CHECKING:
    from harness.tools.permissions import PermissionSet


@dataclass
class ToolContext:
    """
    Context passed to tool execution.

    Contains session information, permissions, and working directory.
    """

    session_id: str
    working_directory: Path
    permissions: PermissionSet
    logger: Any | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class Tool(ABC):
    """
    Abstract base class for all tools.

    Tools are the actions an agent can perform. Each tool must:
    1. Define its name, description, and input schema
    2. Implement the execute method
    3. Optionally implement validation
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name for this tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this tool does."""
        pass

    @property
    def input_schema(self) -> dict[str, Any]:
        """
        JSON Schema for tool inputs.

        Override this to define the expected input structure.
        """
        return {
            "type": "object",
            "properties": {},
            "required": [],
        }

    def to_definition(self) -> dict[str, Any]:
        """Convert tool to API definition format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    @abstractmethod
    async def execute(
        self,
        arguments: dict[str, Any],
        context: ToolContext,
    ) -> ToolResult:
        """
        Execute the tool with given arguments.

        Args:
            arguments: Tool input arguments
            context: Execution context

        Returns:
            ToolResult: Result of execution
        """
        pass

    def validate_arguments(
        self,
        arguments: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """
        Validate tool arguments before execution.

        Override this for custom validation logic.

        Args:
            arguments: Arguments to validate

        Returns:
            tuple: (is_valid, error_message)
        """
        # Basic validation: check required fields
        required = self.input_schema.get("required", [])
        for field_name in required:
            if field_name not in arguments:
                return False, f"Missing required field: {field_name}"

        return True, None

    def __repr__(self) -> str:
        return f"<Tool:{self.name}>"
