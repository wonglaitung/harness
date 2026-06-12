"""
Gateway configuration.

Configuration settings for the Gateway control service.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DockerContainerConfig:
    """Docker container security configuration."""

    image: str = "harness-agent:latest"
    cpu_quota: int = 200000  # 2 CPU (100000 per CPU)
    memory_limit: str = "4g"
    memory_swap: str = "4g"
    timeout_seconds: int = 600  # 10 minutes
    pids_limit: int = 100
    internal_network: str = "harness-net"
    read_only_root_fs: bool = True
    cap_drop: list[str] = field(default_factory=lambda: ["ALL"])


@dataclass
class GatewayConfig:
    """Gateway service configuration."""

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 15

    # Redis
    redis_url: str = "redis://localhost:6379"
    rate_limit_max_requests: int = 100
    rate_limit_window_seconds: int = 3600

    # Docker
    container_config: DockerContainerConfig = field(default_factory=DockerContainerConfig)

    # Container lifecycle management
    container_idle_timeout: int = 900  # 15 minutes (seconds)
    cleanup_interval: int = 300  # 5 minutes (seconds)
    graceful_shutdown_timeout: int = 30  # seconds
    force_kill_timeout: int = 10  # seconds
    max_containers_per_user: int = 3

    # Test mode: shorter timeouts for manual testing
    test_mode: bool = False  # Set to True for testing
    test_idle_timeout: int = 60  # 1 minute in test mode
    test_graceful_shutdown: int = 5  # 5 seconds in test mode

    # Service
    host: str = "0.0.0.0"
    port: int = 8080

    # Environment
    environment: str = "docker"  # "docker" or "k8s"


@dataclass
class Settings:
    """
    Settings from environment variables.

    Environment variables (prefix HARNESS_):
    - HARNESS_JWT_SECRET
    - HARNESS_REDIS_URL
    - HARNESS_ENVIRONMENT
    """

    jwt_secret: Optional[str] = None
    redis_url: Optional[str] = None
    environment: Optional[str] = None

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables."""
        import os

        return cls(
            jwt_secret=os.getenv("HARNESS_JWT_SECRET"),
            redis_url=os.getenv("HARNESS_REDIS_URL"),
            environment=os.getenv("HARNESS_ENVIRONMENT"),
        )