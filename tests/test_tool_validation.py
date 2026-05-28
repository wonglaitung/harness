"""
Tests for Tool JSON Schema validation.
"""

import pytest

from harness.tools.base import Tool, ToolContext
from harness.types import ToolResult


class TestToolValidation:
    """Test tool with complex schema for validation testing."""

    class TestTool(Tool):
        @property
        def name(self) -> str:
            return "test_tool"

        @property
        def description(self) -> str:
            return "Test tool for validation"

        @property
        def input_schema(self) -> dict:
            return {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "number", "minimum": 0},
                    "email": {"type": "string", "format": "email"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "config": {
                        "type": "object",
                        "properties": {
                            "enabled": {"type": "boolean"},
                            "count": {"type": "integer"},
                        },
                    },
                },
                "required": ["name", "age"],
                "additionalProperties": False,
            }

        async def execute(
            self,
            arguments: dict,
            context: ToolContext,
        ) -> ToolResult:
            return ToolResult(
                tool_call_id="test",
                success=True,
                content="OK",
            )


class TestJSONSchemaValidation:
    """Tests for JSON Schema validation."""

    @pytest.fixture
    def tool(self):
        return TestToolValidation.TestTool()

    def test_valid_arguments(self, tool):
        """Test valid arguments pass validation."""
        is_valid, error = tool.validate_arguments({
            "name": "Alice",
            "age": 30,
        })

        assert is_valid is True
        assert error is None

    def test_valid_arguments_with_optional(self, tool):
        """Test valid arguments with optional fields."""
        is_valid, error = tool.validate_arguments({
            "name": "Bob",
            "age": 25,
            "email": "bob@example.com",
            "tags": ["dev", "python"],
            "config": {"enabled": True, "count": 5},
        })

        assert is_valid is True
        assert error is None

    def test_missing_required_field(self, tool):
        """Test missing required field fails validation."""
        is_valid, error = tool.validate_arguments({
            "name": "Charlie",
        })

        assert is_valid is False
        assert "age" in error.lower()

    def test_invalid_type_string_for_number(self, tool):
        """Test invalid type (string for number) fails validation."""
        is_valid, error = tool.validate_arguments({
            "name": "Dave",
            "age": "thirty",  # Should be number
        })

        assert is_valid is False
        assert "number" in error.lower() or "type" in error.lower()

    def test_invalid_type_number_for_string(self, tool):
        """Test invalid type (number for string) fails validation."""
        is_valid, error = tool.validate_arguments({
            "name": 123,  # Should be string
            "age": 30,
        })

        assert is_valid is False

    def test_invalid_minimum(self, tool):
        """Test minimum constraint validation."""
        is_valid, error = tool.validate_arguments({
            "name": "Eve",
            "age": -5,  # Minimum is 0
        })

        assert is_valid is False
        assert "minimum" in error.lower() or "0" in error

    def test_invalid_array_item_type(self, tool):
        """Test array item type validation."""
        is_valid, error = tool.validate_arguments({
            "name": "Frank",
            "age": 40,
            "tags": ["valid", 123],  # 123 is not a string
        })

        assert is_valid is False

    def test_additional_properties_rejected(self, tool):
        """Test additional properties are rejected."""
        is_valid, error = tool.validate_arguments({
            "name": "Grace",
            "age": 35,
            "unknown_field": "value",  # Not in schema
        })

        assert is_valid is False
        assert "additional" in error.lower()

    def test_nested_object_validation(self, tool):
        """Test nested object validation."""
        is_valid, error = tool.validate_arguments({
            "name": "Henry",
            "age": 50,
            "config": {
                "enabled": "yes",  # Should be boolean
            },
        })

        assert is_valid is False


class TestBasicValidation:
    """Tests for basic validation fallback."""

    class SimpleTool(Tool):
        @property
        def name(self) -> str:
            return "simple_tool"

        @property
        def description(self) -> str:
            return "Simple tool"

        @property
        def input_schema(self) -> dict:
            return {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                },
                "required": ["path"],
            }

        async def execute(
            self,
            arguments: dict,
            context: ToolContext,
        ) -> ToolResult:
            return ToolResult(tool_call_id="test", success=True, content="OK")

    def test_basic_validate_missing_required(self):
        """Test basic validation for missing required field."""
        tool = self.SimpleTool()
        is_valid, error = tool._basic_validate({})

        assert is_valid is False
        assert "path" in error

    def test_basic_validate_present(self):
        """Test basic validation when required field is present."""
        tool = self.SimpleTool()
        is_valid, error = tool._basic_validate({"path": "/test"})

        assert is_valid is True
        assert error is None


class TestEdgeCases:
    """Test edge cases in validation."""

    class AnySchemaTool(Tool):
        """Tool with minimal schema."""

        @property
        def name(self) -> str:
            return "any_tool"

        @property
        def description(self) -> str:
            return "Accepts any input"

        @property
        def input_schema(self) -> dict:
            return {"type": "object"}

        async def execute(
            self,
            arguments: dict,
            context: ToolContext,
        ) -> ToolResult:
            return ToolResult(tool_call_id="test", success=True, content="OK")

    def test_empty_schema_accepts_anything(self):
        """Test that minimal schema accepts any object."""
        tool = self.AnySchemaTool()

        is_valid, error = tool.validate_arguments({"anything": "goes"})

        assert is_valid is True
        assert error is None

    def test_empty_arguments(self):
        """Test empty arguments with minimal schema."""
        tool = self.AnySchemaTool()

        is_valid, error = tool.validate_arguments({})

        assert is_valid is True
