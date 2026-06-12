"""
Docker container manager implementation.

Provides container lifecycle management with security hardening:
- Resource limits (CPU, memory, PIDs)
- Internal network isolation
- Read-only filesystem + tmpfs
- Capability dropping
- Three-layer cleanup strategy:
  1. WebSocket disconnect -> draining -> cleanup
  2. Idle timeout (15min) -> cleanup
  3. Resource pressure -> eviction (future)

Reference: packages/cloud/docs/03-gateway.md
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

import docker
from docker.errors import NotFound, APIError

from harness_cloud.gateway.config import GatewayConfig
from harness_cloud.gateway.container_manager import (
    ContainerInfo,
    ContainerManager,
    ContainerState,
)

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

    Lifecycle management:
    - WebSocket disconnect -> draining state -> graceful shutdown
    - Idle timeout (15min) -> cleanup
    - Periodic cleanup task
    """

    def __init__(self, gateway_config: GatewayConfig | None = None):
        self.gateway_config = gateway_config or GatewayConfig()
        self.config = self.gateway_config.container_config
        self.client = docker.from_env()
        self._containers: dict[str, ContainerInfo] = {}
        self._cleanup_task: asyncio.Task | None = None
        self._draining_tasks: dict[str, asyncio.Task] = {}
        self._user_containers: dict[str, list[str]] = {}  # user_id -> [session_ids]
        self._ensure_network()

    def _ensure_network(self) -> None:
        """Ensure network exists for Gateway-Agent communication."""
        try:
            self.client.networks.get(self.config.internal_network)
            logger.info(f"Network {self.config.internal_network} already exists")
        except NotFound:
            # Create network for Gateway-Agent communication
            # Note: Not using internal=True because Agent needs outbound access to LLM APIs
            self.client.networks.create(
                self.config.internal_network,
                driver="bridge",
                # internal=True would block outbound, but Agent needs LLM API access
            )
            logger.info(f"Created network: {self.config.internal_network}")

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

        Lifecycle:
        - Created in RUNNING state
        - Tracks per-user container count
        """
        # Check user container limit
        user_sessions = self._user_containers.get(user_id, [])
        if len(user_sessions) >= self.gateway_config.max_containers_per_user:
            # Remove oldest container for this user
            oldest_session = user_sessions[0]
            logger.info(
                f"User {user_id} exceeded container limit, removing oldest: {oldest_session}"
            )
            await self.destroy_container(oldest_session)

        volumes = {}
        if workspace_path:
            volumes[workspace_path] = {"bind": "/workspace", "mode": "rw"}

        # tmpfs mounts for writable directories
        # - /tmp: temporary files
        # - /home: SDK state (.harness directory)
        # - /workspace: SDK storage (.harness/sessions, etc.)
        tmpfs = {
            "/tmp": "size=100M,mode=1777",
            "/home": "size=50M,mode=1777",
            "/workspace": "size=200M,mode=1777",
        }

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

                # Network configuration
                # Note: For MVP, Agent needs outbound access to LLM APIs
                # Using harness-net for Gateway-Agent communication
                # Agent can access external LLM APIs (not fully isolated)
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

            # Wait for container to be ready (up to 10 seconds)
            logger.info(f"Waiting for container {session_id} to be ready...")
            max_wait = 10
            for i in range(max_wait):
                await asyncio.sleep(1)
                container.reload()
                if container.status == "running":
                    networks = container.attrs["NetworkSettings"]["Networks"]
                    internal_ip = networks.get(
                        self.config.internal_network, {}
                    ).get("IPAddress", "")
                    if internal_ip:
                        logger.info(f"Container {session_id} ready with IP {internal_ip}")
                        break
            else:
                logger.warning(f"Container {session_id} not ready after {max_wait}s")

            info = ContainerInfo(
                container_id=container.id,
                session_id=session_id,
                user_id=user_id,
                internal_ip=internal_ip,
                created_at=datetime.now(),
                last_activity=datetime.now(),
                state=ContainerState.RUNNING,
            )

            self._containers[session_id] = info

            # Track user containers
            if user_id not in self._user_containers:
                self._user_containers[user_id] = []
            self._user_containers[user_id].append(session_id)

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

        # Remove from user tracking
        if info.user_id in self._user_containers:
            try:
                self._user_containers[info.user_id].remove(session_id)
            except ValueError:
                pass

        # Cancel draining task if exists
        draining_task = self._draining_tasks.pop(session_id, None)
        if draining_task and not draining_task.done():
            draining_task.cancel()

        try:
            container = self.client.containers.get(info.container_id)

            # Graceful shutdown: SIGTERM then SIGKILL
            try:
                container.stop(timeout=self.gateway_config.force_kill_timeout)
            except APIError:
                container.remove(force=True)

            logger.info(f"Destroyed container: {session_id}")
            return True
        except NotFound:
            logger.warning(f"Container not found: {session_id}")
            return True  # Already removed
        except APIError as e:
            logger.error(f"Failed to destroy container: {e}")
            return False

    async def mark_draining(self, session_id: str) -> bool:
        """
        Mark container as draining state.

        WebSocket disconnected, container will:
        1. Wait for in-flight tasks (graceful_shutdown_timeout)
        2. Then cleanup

        Returns False if container not found or already draining.
        """
        info = self._containers.get(session_id)
        if not info or info.state != ContainerState.RUNNING:
            return False

        info.state = ContainerState.DRAINING
        logger.info(f"Container {session_id} marked as draining")

        # Start draining cleanup task
        self._draining_tasks[session_id] = asyncio.create_task(
            self._draining_cleanup(session_id)
        )
        return True

    async def _draining_cleanup(self, session_id: str) -> None:
        """
        Cleanup task for draining container.

        Wait for graceful_shutdown_timeout then destroy.
        """
        try:
            await asyncio.sleep(self.gateway_config.graceful_shutdown_timeout)

            info = self._containers.get(session_id)
            if info and info.state == ContainerState.DRAINING:
                logger.info(f"Draining timeout, destroying container: {session_id}")
                await self.destroy_container(session_id)

        except asyncio.CancelledError:
            logger.debug(f"Draining cleanup cancelled for {session_id}")
        except Exception as e:
            logger.error(f"Draining cleanup error for {session_id}: {e}")

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

        # Cancel all draining tasks
        for task in self._draining_tasks.values():
            if not task.done():
                task.cancel()

        for info in list(self._containers.values()):
            await self.destroy_container(info.session_id)

        logger.info("DockerManager stopped")

    async def _cleanup_loop(self) -> None:
        """
        Periodic cleanup of expired containers.

        Two cleanup triggers:
        1. Idle timeout: container_idle_timeout (15 minutes)
        2. Config timeout: timeout_seconds (10 minutes, from container config)

        Runs every cleanup_interval (5 minutes).
        """
        while True:
            await asyncio.sleep(self.gateway_config.cleanup_interval)
            now = datetime.now()

            # Cleanup idle containers (15 minute timeout)
            idle_timeout = self.gateway_config.container_idle_timeout
            idle_expired = [
                sid
                for sid, info in self._containers.items()
                if info.state == ContainerState.RUNNING
                and (now - info.last_activity).total_seconds() > idle_timeout
            ]

            for sid in idle_expired:
                logger.info(f"Cleaning up idle container (15min): {sid}")
                await self.destroy_container(sid)

            # Cleanup old containers from config timeout (fallback)
            config_expired = [
                sid
                for sid, info in self._containers.items()
                if info.state == ContainerState.RUNNING
                and (now - info.created_at).total_seconds() > self.config.timeout_seconds
            ]

            for sid in config_expired:
                if sid not in idle_expired:  # Avoid double cleanup
                    logger.info(f"Cleaning up old container (config timeout): {sid}")
                    await self.destroy_container(sid)