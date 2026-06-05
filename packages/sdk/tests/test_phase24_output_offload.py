"""
Tests for Phase 24: Tool Output Offload
"""

import tempfile
from pathlib import Path

import pytest

from harness.core.output_offload import (
    OffloadConfig,
    OffloadedOutput,
    OutputOffloader,
)
from harness.types import ToolResult


class TestOffloadConfig:
    """Tests for OffloadConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = OffloadConfig()
        assert config.size_threshold_chars == 5000
        assert config.size_threshold_tokens == 1250
        assert config.max_outputs_per_session == 50
        assert config.cleanup_on_session_end is False
        assert config.preview_length == 200

    def test_custom_config(self):
        """Test custom configuration values."""
        config = OffloadConfig(
            size_threshold_chars=1000,
            max_outputs_per_session=10,
            preview_length=100,
        )
        assert config.size_threshold_chars == 1000
        assert config.max_outputs_per_session == 10
        assert config.preview_length == 100

    def test_invalid_threshold(self):
        """Test invalid size threshold raises error."""
        with pytest.raises(ValueError, match="size_threshold_chars must be at least 100"):
            OffloadConfig(size_threshold_chars=50)

    def test_invalid_max_outputs(self):
        """Test invalid max outputs raises error."""
        with pytest.raises(ValueError, match="max_outputs_per_session must be at least 1"):
            OffloadConfig(max_outputs_per_session=0)

    def test_invalid_preview_length(self):
        """Test invalid preview length raises error."""
        with pytest.raises(ValueError, match="preview_length must be at least 50"):
            OffloadConfig(preview_length=10)


class TestOffloadedOutput:
    """Tests for OffloadedOutput."""

    def test_get_reference_string(self):
        """Test reference string generation."""
        output = OffloadedOutput(
            file_path=Path("/tmp/test.txt"),
            tool_name="test_tool",
            tool_call_id="call_123",
            original_size=10000,
            preview="This is a preview...",
        )
        ref = output.get_reference_string()
        assert "[Output from test_tool (10000 chars)]" in ref
        assert "Preview: This is a preview..." in ref
        assert "Full output saved to: /tmp/test.txt" in ref

    def test_get_reference_string_with_summary(self):
        """Test reference string with summary."""
        output = OffloadedOutput(
            file_path=Path("/tmp/test.txt"),
            tool_name="test_tool",
            tool_call_id="call_123",
            original_size=10000,
            preview="This is a preview...",
            summary="File listing of directory",
        )
        ref = output.get_reference_string()
        assert "Summary: File listing of directory" in ref

    def test_serialization(self):
        """Test serialization and deserialization."""
        output = OffloadedOutput(
            file_path=Path("/tmp/test.txt"),
            tool_name="test_tool",
            tool_call_id="call_123",
            original_size=10000,
            preview="Preview",
            session_id="session_1",
        )
        data = output.to_dict()
        restored = OffloadedOutput.from_dict(data)

        assert str(restored.file_path) == str(output.file_path)
        assert restored.tool_name == output.tool_name
        assert restored.tool_call_id == output.tool_call_id
        assert restored.original_size == output.original_size
        assert restored.preview == output.preview


class TestOutputOffloader:
    """Tests for OutputOffloader."""

    def test_should_offload_below_threshold(self):
        """Test that small outputs are not offloaded."""
        offloader = OutputOffloader(OffloadConfig(size_threshold_chars=1000))
        assert offloader.should_offload("small content", "session_1") is False

    def test_should_offload_above_threshold(self):
        """Test that large outputs are offloaded."""
        offloader = OutputOffloader(OffloadConfig(size_threshold_chars=100))
        large_content = "x" * 200
        assert offloader.should_offload(large_content, "session_1") is True

    def test_should_offload_respects_session_limit(self):
        """Test session limit is respected."""
        offloader = OutputOffloader(OffloadConfig(
            size_threshold_chars=100,
            max_outputs_per_session=2,
        ))
        large_content = "x" * 200

        assert offloader.should_offload(large_content, "session_1") is True
        offloader.offload(large_content, "tool1", "call1", "session_1")

        assert offloader.should_offload(large_content, "session_1") is True
        offloader.offload(large_content, "tool2", "call2", "session_1")

        # Third offload should be blocked
        assert offloader.should_offload(large_content, "session_1") is False

    def test_offload_creates_file(self):
        """Test that offload creates a file."""
        offloader = OutputOffloader()
        large_content = "x" * 6000

        output = offloader.offload(
            content=large_content,
            tool_name="test_tool",
            tool_call_id="call_123",
            session_id="session_1",
        )

        assert output.file_path.exists()
        assert output.original_size == 6000
        assert output.tool_name == "test_tool"
        assert output.tool_call_id == "call_123"

        # Verify file content
        loaded = offloader.load_offloaded(output.file_path)
        assert loaded == large_content

        # Cleanup
        output.file_path.unlink()

    def test_offload_creates_preview(self):
        """Test that offload creates preview."""
        config = OffloadConfig(size_threshold_chars=100, preview_length=50)
        offloader = OutputOffloader(config)
        large_content = "x" * 200

        output = offloader.offload(large_content, "tool", "call", "session")

        assert len(output.preview) == 53  # 50 + "..."
        assert output.preview.endswith("...")

        # Cleanup
        output.file_path.unlink()

    def test_create_offloaded_result(self):
        """Test creating offloaded ToolResult."""
        offloader = OutputOffloader(OffloadConfig(size_threshold_chars=100))
        large_content = "x" * 200

        original = ToolResult(
            tool_call_id="call_123",
            success=True,
            content=large_content,
            metadata={"tool_name": "test_tool"},
        )

        result = offloader.create_offloaded_result(original, "session_1")

        assert result.success is True
        assert "[Output from test_tool (200 chars)]" in result.content
        assert result.metadata.get("offloaded") is True
        assert "offload_path" in result.metadata

        # Cleanup
        offloader.cleanup_session("session_1")

    def test_cleanup_session(self):
        """Test session cleanup."""
        offloader = OutputOffloader(OffloadConfig(size_threshold_chars=100))
        large_content = "x" * 200

        # Create multiple offloads
        offloader.offload(large_content, "tool1", "call1", "session_1")
        offloader.offload(large_content, "tool2", "call2", "session_1")

        outputs = offloader.get_session_outputs("session_1")
        assert len(outputs) == 2

        # Cleanup
        deleted = offloader.cleanup_session("session_1")
        assert deleted == 2

        outputs = offloader.get_session_outputs("session_1")
        assert len(outputs) == 0

    def test_get_stats(self):
        """Test statistics."""
        offloader = OutputOffloader(OffloadConfig(size_threshold_chars=100))
        large_content = "x" * 200

        offloader.offload(large_content, "tool1", "call1", "session_1")
        offloader.offload(large_content, "tool2", "call2", "session_2")

        stats = offloader.get_stats()
        assert stats["active_files"] == 2
        assert stats["sessions_with_outputs"] == 2
        assert stats["total_original_size"] == 400

        # Cleanup
        offloader.cleanup_all()

    def test_empty_content_not_offloaded(self):
        """Test that empty content is not offloaded."""
        offloader = OutputOffloader()
        assert offloader.should_offload("", "session_1") is False


class TestOutputOffloaderIntegration:
    """Integration tests for OutputOffloader with real files."""

    def test_temp_directory_creation(self):
        """Test that temp directory is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = OffloadConfig(temp_dir=Path(tmpdir))
            offloader = OutputOffloader(config)

            # When custom temp_dir is provided, use it directly
            assert offloader._temp_dir.exists()
            assert offloader._temp_dir == Path(tmpdir)

    def test_default_temp_directory(self):
        """Test default temp directory is .harness/offload in cwd."""
        offloader = OutputOffloader()
        assert offloader._temp_dir == Path.cwd() / ".harness" / "offload"
        assert offloader._temp_dir.exists()

    def test_custom_temp_dir(self):
        """Test custom temp directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = OffloadConfig(temp_dir=Path(tmpdir) / "custom")
            offloader = OutputOffloader(config)

            large_content = "x" * 6000
            output = offloader.offload(large_content, "tool", "call", "session")

            assert output.file_path.exists()
            assert str(tmpdir) in str(output.file_path)

            # Cleanup
            offloader.cleanup_all()
