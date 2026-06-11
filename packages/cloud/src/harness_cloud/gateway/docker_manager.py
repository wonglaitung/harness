"""
Docker container manager implementation.

Provides container lifecycle management with security hardening:
- Resource limits (CPU, memory, PIDs)
- Internal network isolation
- Read-only filesystem + tmpfs
- Capability dropping

Reference: packages/cloud/docs/03-gateway.md
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

import docker
from docker.errors import NotFound, APIError

from harness_cloud.gateway.config import DockerContainerConfig
from harness_cloud.gateway.container_manager import ContainerInfo, ContainerManager

logger = logging.getLogger(__name__)


class DockerManager(ContainerManager):
    """
    Docker environment container manager.

    Security hardening (ADR-004, ADR-007, ADR-008):
    - pids_limit: 100 (prevent fork bombs)
    - internal_network: harness-net (no external access)
    - read_only_root_fs: True
    - cap_drop: ALL
    - tmpfs mount for /tmp
    """

    def __init__(self, config: DockerContainerConfig | None = None):
        self.config = config or DockerContainerConfig()
        self.client = docker.from_env()
        self._containers: dict[str, ContainerInfo] = {}
        self._cleanup_task: asyncio.Task | None = None
        self._ensure_network()

    def _ensure_network(self) -> None:
        """Ensure internal network exists."""
        try:
            self.client.networks.get(self.config.internal_network)
            logger.info(f"Network {self.config.internal_network} already exists")
        except NotFound:
            # Create internal network (blocks external access)
            self.client.networks.create(
                self.config.internal_network,
                driver="bridge",
                internal=True,  # Key: blocks external internet access
            )
            logger.info(f"Created internal network: {self.config.internal_network}")

    async def create_container(
        self,
        session_id: str,
        user_id: str,
        workspace_path: str | None = None,
    ) -> ContainerInfo:
        """
        Create hardened sandbox container.

        Security measures:
        1. Resource limits: CPU, memory, PIDs
        2. Network: internal only (no external access)
        3. Filesystem: read-only + tmpfs
        4. Capabilities: drop all
        """
        volumes = {}
        if workspace_path:
            volumes[workspace_path] = {"bind": "/workspace", "mode": "rw"}

        # tmpfs mount (fix read-only filesystem issue)
        tmpfs = {"/tmp": "size=100M,mode=1777"}

        try:
            container = self.client.containers.run(
                self.config.image,
                detach=True,
                name=f"harness-{session_id}",
                environment={
                    "SESSION_ID": session_id,
                    "USER_ID": user_id,
                },
                volumes=volumes,
                tmpfs=tmpfs,

                # Resource limits
                cpu_quota=self.config.cpu_quota,
                mem_limit=self.config.memory_limit,
                memswap_limit=self.config.memory_swap,
                pids_limit=self.config.pids_limit,

                # Network: internal only
                network=self.config.internal_network,

                # Security hardening
                security_opt=["no-new-privileges"],
                cap_drop=self.config.cap_drop,
                read_only=self.config.read_only_root_fs,

                remove=False,
            )

            # Get container IP
            container.reload()
            networks = container.attrs["NetworkSettings"]["Networks"]
            internal_ip = networks.get(
                self.config.internal_network, {}
            ).get("IPAddress", "")

            info = ContainerInfo(
                container_id=container.id,
                session_id=session_id,
                user_id=user_id,
                internal_ip=internal_ip,
                created_at=datetime.now(),
                last_activity=datetime.now(),
            )

            self._containers[session_id] = info
            logger.info(f"Created container: {session_id} ({container.id[:12]})")
            return info

        except APIError as e:
            logger.error(f"Failed to create container: {e}")
            raise

    async def destroy_container(self, session_id: str) -> bool:
        """Destroy container."""
        info = self._containers.pop(session_id, None)
        if not info:
            return False

        try:
            container = self.client.containers.get(info.container_id)
            container.remove(force=True)
            logger.info(f"Destroyed container: {session_id}")
            return True
        except NotFound:
            logger.warning(f"Container not found: {session_id}")
            return False
        except APIError as e:
            logger.error(f"Failed to destroy container: {e}")
            return False

    def get_container_url(self, session_id: str) -> str:
        """Get container WebSocket URL."""
        info = self._containers.get(session_id)
        if not info:
            raise ValueError(f"Container not found: {session_id}")
        return f"ws://{info.internal_ip}:{info.internal_port}/ws/run"

    def get_container(self, session_id: str) -> ContainerInfo | None:
        """Get container info."""
        return self._containers.get(session_id)

    async def start(self) -> None:
        """Start cleanup task."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("DockerManager started")

    async def stop(self) -> None:
        """Stop and cleanup all containers."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        for info in list(self._containers.values()):
            await self.destroy_container(info.session_id)

        logger.info("DockerManager stopped")

    async def _cleanup_loop(self) -> None:
        """
        Periodic cleanup of expired containers.

        Runs every 60 seconds, destroys containers that have been
        inactive for longer than timeout_seconds.
        """
        while True:
            await asyncio.sleep(60)
            now = datetime.now()
            expired = [
                sid
                for sid, info in self._containers.items()
                if (now - info.last_activity).total_seconds() > self.config.timeout_seconds
            ]
            for sid in expired:
                logger.info(f"Cleaning up expired container: {sid}")
                await self.destroy_container(sid)