"""
MCP Tool Wrapper.

Wraps MCP tools as Harness Tool instances.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

from harness.types import ToolResult

if TYPE_CHECKING:
    from harness.mcp.client import MCPClient
    from harness.tools.executor import ToolContext


class MCPToolWrapper:
    """
    Wrapper to expose MCP tools as Harness Tools.

    Allows MCP server tools to be used seamlessly
    within the Harness tool system.
    """

    def __init__(
        self,
        mcp_client: "MCPClient",
        server_name: str,
        tool_name: str,
        description: str,
        input_schema: Dict[str, Any],
        timeout: float = 30.0,
    ):
        """
        Initialize MCP tool wrapper.

        Args:
            mcp_client: Connected MCP client
            server_name: MCP server name
            tool_name: Original tool name on MCP server
            description: Tool description
            input_schema: Tool input schema (JSON Schema format)
            timeout: Execution timeout in seconds
        """
        # Tool name is prefixed with server name to avoid conflicts
        self._name = f"mcp_{server_name}_{tool_name}"
        self._server_name = server_name
        self._original_name = tool_name

        self._mcp_client = mcp_client
        self._description = description
        self._input_schema = input_schema
        self._timeout = timeout

        # Extract properties and required from input_schema
        self._parameters = input_schema.get("properties", {})
        self._required = input_schema.get("required", [])

    @property
    def name(self) -> str:
        """Tool name (with server prefix)."""
        return self._name

    @property
    def original_name(self) -> str:
        """Original tool name on MCP server."""
        return self._original_name

    @property
    def server_name(self) -> str:
        """MCP server name."""
        return self._server_name

    @property
    def description(self) -> str:
        """Tool description."""
        return self._description

    @property
    def parameters(self) -> Dict[str, Any]:
        """Parameter definitions."""
        return self._parameters

    @property
    def required(self) -> List[str]:
        """Required parameters."""
        return self._required

    @property
    def input_schema(self) -> Dict[str, Any]:
        """Tool input schema (JSON Schema format)."""
        return self._input_schema

    def validate_arguments(
        self,
        arguments: Dict[str, Any],
    ) -> tuple[bool, str | None]:
        """
        Validate tool arguments using JSON Schema.

        Args:
            arguments: Arguments to validate

        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            import jsonschema

            jsonschema.validate(arguments, self._input_schema)
            return True, None

        except ImportError:
            # Fall back to basic validation
            for field_name in self._required:
                if field_name not in arguments:
                    return False, f"Missing required field: {field_name}"
            return True, None

        except jsonschema.ValidationError as e:
            return False, str(e.message)

        except jsonschema.SchemaError as e:
            return False, f"Invalid schema: {e.message}"

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Optional["ToolContext"] = None,
    ) -> ToolResult:
        """
        Execute MCP tool.

        Args:
            arguments: Tool arguments
            context: Execution context (optional for MCP tools)

        Returns:
            Tool execution result
        """
        try:
            result = await self._mcp_client.call_tool(
                self._original_name,
                arguments,
                timeout=self._timeout,
            )

            if result.get("is_error"):
                return ToolResult(
                    tool_call_id="",
                    success=False,
                    content="",
                    error=result.get("content", "MCP tool error"),
                )

            return ToolResult(
                tool_call_id="",
                success=True,
                content=result.get("content", ""),
                metadata={
                    "server": self._server_name,
                    "tool": self._original_name,
                },
            )

        except Exception as e:
            return ToolResult(
                tool_call_id="",
                success=False,
                content="",
                error=f"MCP tool execution failed: {e}",
            )

    def to_definition(self) -> Dict[str, Any]:
        """
        Convert to tool definition format (same as Anthropic schema).

        Returns:
            Tool definition dict
        """
        return {
            "name": self._name,
            "description": self._description,
            "input_schema": self._input_schema,
        }

    def to_anthropic_schema(self) -> Dict[str, Any]:
        """
        Convert to Anthropic tool schema format.

        Returns:
            Anthropic-compatible tool schema
        """
        return self.to_definition()

    def to_openai_schema(self) -> Dict[str, Any]:
        """
        Convert to OpenAI tool schema format.

        Returns:
            OpenAI-compatible tool schema
        """
        return {
            "type": "function",
            "function": {
                "name": self._name,
                "description": self._description,
                "parameters": self._input_schema,
            },
        }