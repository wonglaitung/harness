"""
Container manager abstract interface.

Provides abstraction for different container runtime backends:
- DockerManager (Docker environment)
- K8sPodManager (Kubernetes environment)

Reference: packages/cloud/docs/03-gateway.md
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ContainerInfo:
    """Runtime container information."""

    container_id: str
    session_id: str
    user_id: str
    internal_ip: str
    created_at: datetime
    last_activity: datetime
    internal_port: int = 8000


class ContainerManager(ABC):
    """
    Container manager abstract interface.

    Implementations:
    - DockerManager: Docker environment
    - K8sPodManager: Kubernetes environment (future)
    """

    @abstractmethod
    async def create_container(
        self,
        session_id: str,
        user_id: str,
        workspace_path: str | None = None,
    ) -> ContainerInfo:
        """
        Create sandbox container.

        Args:
            session_id: Session identifier
            user_id: User identifier
            workspace_path: Optional workspace mount path

        Returns:
            ContainerInfo with runtime details
        """
        pass

    @abstractmethod
    async def destroy_container(self, session_id: str) -> bool:
        """
        Destroy container.

        Args:
            session_id: Session identifier

        Returns:
            True if successfully destroyed
        """
        pass

    @abstractmethod
    def get_container_url(self, session_id: str) -> str:
        """
        Get container WebSocket URL.

        Args:
            session_id: Session identifier

        Returns:
            WebSocket URL for container connection
        """
        pass

    @abstractmethod
    def get_container(self, session_id: str) -> ContainerInfo | None:
        """
        Get container info.

        Args:
            session_id: Session identifier

        Returns:
            ContainerInfo if exists, None otherwise
        """
        pass

    @abstractmethod
    async def start(self) -> None:
        """Start background tasks (cleanup loop, etc.)."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop and cleanup all containers."""
        pass