"""
Tests for Sub-Agent Management.
"""

import pytest

from harness.core.subagent import (
    SubAgentConfig,
    SubAgentManager,
    SubAgentResult,
    SubAgentStatus,
)
from harness.testing.mock_harness import MockHarness, MockHarnessConfig, MockResponse


class MockLLMClient:
    """Mock LLM client for testing."""

    @property
    def model_name(self):
        return "mock-model"

    async def call(self, messages, tools=None, system=None):
        from harness.types import LLMResponse, TokenUsage, StopReason
        return LLMResponse(
            content="Mock response",
            stop_reason=StopReason.END_TURN,
            usage=TokenUsage(input_tokens=10, output_tokens=10),
        )


class TestSubAgentConfig:
    """Test SubAgentConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = SubAgentConfig(
            name="test_agent",
            task="Test task",
        )
        assert config.name == "test_agent"
        assert config.task == "Test task"
        assert config.max_iterations == 20
        assert config.inherit_context is False
        assert config.report_format == "summary"
        assert config.tools is None

    def test_custom_config(self):
        """Test custom configuration."""
        config = SubAgentConfig(
            name="custom_agent",
            task="Custom task",
            max_iterations=50,
            inherit_context=True,
            report_format="full",
            tools=["read", "write"],
            timeout=60.0,
        )
        assert config.max_iterations == 50
        assert config.inherit_context is True
        assert config.report_format == "full"
        assert config.tools == ["read", "write"]
        assert config.timeout == 60.0


class TestSubAgentResult:
    """Test SubAgentResult."""

    def test_success_result(self):
        """Test creating a successful result."""
        result = SubAgentResult(
            name="test_agent",
            success=True,
            status=SubAgentStatus.COMPLETED,
            summary="Task completed successfully",
            iterations=5,
        )
        assert result.success is True
        assert result.status == SubAgentStatus.COMPLETED
        assert result.summary == "Task completed successfully"
        assert result.error is None

    def test_failure_result(self):
        """Test creating a failed result."""
        result = SubAgentResult(
            name="test_agent",
            success=False,
            status=SubAgentStatus.FAILED,
            error="Timeout exceeded",
        )
        assert result.success is False
        assert result.status == SubAgentStatus.FAILED
        assert result.error == "Timeout exceeded"

    def test_structured_result(self):
        """Test structured result format."""
        result = SubAgentResult(
            name="test_agent",
            success=True,
            status=SubAgentStatus.COMPLETED,
            structured_result={
                "files_analyzed": 10,
                "issues_found": 3,
            },
        )
        assert result.structured_result["files_analyzed"] == 10
        assert result.structured_result["issues_found"] == 3


class TestSubAgentManager:
    """Test SubAgentManager."""

    def test_init(self):
        """Test manager initialization."""
        # Mock parent agent
        class MockParent:
            config = type('Config', (), {'model': 'test-model'})()

        manager = SubAgentManager(MockParent())
        assert manager.list_sub_agents() == []

    @pytest.mark.asyncio
    async def test_spawn_sub_agent(self):
        """Test spawning a sub-agent."""
        class MockParent:
            config = type('Config', (), {'model': 'test-model'})()

        manager = SubAgentManager(MockParent())

        config = SubAgentConfig(
            name="analyzer",
            task="Analyze code",
        )
        mock_llm = MockLLMClient()
        name = await manager.spawn(config, llm_client=mock_llm)

        assert name == "analyzer"
        assert "analyzer" in manager.list_sub_agents()
        assert manager.get_status("analyzer") == SubAgentStatus.PENDING

    @pytest.mark.asyncio
    async def test_spawn_multiple_sub_agents(self):
        """Test spawning multiple sub-agents."""
        class MockParent:
            config = type('Config', (), {'model': 'test-model'})()

        manager = SubAgentManager(MockParent())
        mock_llm = MockLLMClient()

        await manager.spawn(SubAgentConfig(name="agent1", task="Task 1"), llm_client=mock_llm)
        await manager.spawn(SubAgentConfig(name="agent2", task="Task 2"), llm_client=mock_llm)
        await manager.spawn(SubAgentConfig(name="agent3", task="Task 3"), llm_client=mock_llm)

        agents = manager.list_sub_agents()
        assert len(agents) == 3
        assert "agent1" in agents
        assert "agent2" in agents
        assert "agent3" in agents

    @pytest.mark.asyncio
    async def test_cancel_sub_agent(self):
        """Test cancelling a sub-agent."""
        class MockParent:
            config = type('Config', (), {'model': 'test-model'})()

        manager = SubAgentManager(MockParent())
        mock_llm = MockLLMClient()

        await manager.spawn(SubAgentConfig(name="test", task="Test"), llm_client=mock_llm)

        # Cancel a pending agent (won't work as it's not running)
        cancelled = await manager.cancel("test")
        assert cancelled is False

    def test_clear(self):
        """Test clearing all sub-agents."""
        class MockParent:
            config = type('Config', (), {'model': 'test-model'})()

        manager = SubAgentManager(MockParent())
        manager._sub_agents["a"] = None
        manager._sub_agents["b"] = None

        manager.clear()

        assert manager.list_sub_agents() == []
        assert manager.get_all_results() == {}

    def test_get_result_not_found(self):
        """Test getting result for non-existent agent."""
        class MockParent:
            config = type('Config', (), {'model': 'test-model'})()

        manager = SubAgentManager(MockParent())
        result = manager.get_result("nonexistent")
        assert result is None

    def test_get_status_not_found(self):
        """Test getting status for non-existent agent."""
        class MockParent:
            config = type('Config', (), {'model': 'test-model'})()

        manager = SubAgentManager(MockParent())
        status = manager.get_status("nonexistent")
        assert status is None


class TestSubAgentStatus:
    """Test SubAgentStatus enum."""

    def test_status_values(self):
        """Test that all statuses have correct values."""
        assert SubAgentStatus.PENDING.value == "pending"
        assert SubAgentStatus.RUNNING.value == "running"
        assert SubAgentStatus.COMPLETED.value == "completed"
        assert SubAgentStatus.FAILED.value == "failed"
        assert SubAgentStatus.CANCELLED.value == "cancelled"
