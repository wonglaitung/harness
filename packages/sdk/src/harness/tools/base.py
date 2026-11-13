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

    治理声明（设计稿 §6.3 / §6.4）：`capability` 与 `idempotent` 是治理块的
    必备字段——**缺声明即拒绝注册**（不保留 `unknown` 后门）。但基类不能强制
    子类实现（否则所有既有工具都要改），因此这里给"未声明"哨兵，由注册期
    校验（`harness.governance.gateway`）在 strict 下拒绝。
    """

    #: 能力分级：read / write / payment / destructive。未声明时为 None。
    capability: str | None = None
    #: 重复调用是否不产生额外业务效果。未声明时为 None。
    idempotent: bool | None = None
    #: 业务参数约束（§6.4）。自研工具在代码里声明；MCP 工具在治理块声明。
    constraints: dict[str, Any] | None = None

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
        Validate tool arguments using JSON Schema.

        Falls back to basic validation if jsonschema is not installed.

        Args:
            arguments: Arguments to validate

        Returns:
            tuple: (is_valid, error_message)
        """
        # Try to use jsonschema for full validation
        try:
            import jsonschema

            jsonschema.validate(arguments, self.input_schema)
            return True, None

        except ImportError:
            # Fall back to basic validation
            return self._basic_validate(arguments)

        except jsonschema.ValidationError as e:
            return False, str(e.message)

        except jsonschema.SchemaError as e:
            return False, f"Invalid schema: {e.message}"

    def _basic_validate(self, arguments: dict[str, Any]) -> tuple[bool, str | None]:
        """
        Basic validation when jsonschema is not available.

        Only checks for required fields.

        Args:
            arguments: Arguments to validate

        Returns:
            tuple: (is_valid, error_message)
        """
        required = self.input_schema.get("required", [])
        for field_name in required:
            if field_name not in arguments:
                return False, f"Missing required field: {field_name}"

        return True, None

    def __repr__(self) -> str:
        return f"<Tool:{self.name}>"
