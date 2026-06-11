"""
Agent configuration.

Configuration settings for the Container Agent service.
"""

from dataclasses import dataclass


@dataclass
class AgentConfig:
    """Agent service configuration."""

    # Workspace
    workspace: str = "/workspace"

    # Default model settings
    default_model: str = "claude-sonnet-4-6"
    default_max_iterations: int = 10
    default_temperature: float = 1.0

    # Memory limits (soft limit in bytes)
    memory_soft_limit: int = 3800 * 1024 * 1024  # 3.8GB
    memory_hard_limit: int = 4000 * 1024 * 1024  # 4GB

    # Heartbeat settings
    heartbeat_timeout: float = 90.0  # seconds

    # Tool result truncation
    tool_result_max_length: int = 500
