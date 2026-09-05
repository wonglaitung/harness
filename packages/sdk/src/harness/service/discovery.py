"""
Service discovery integration for Spring Cloud.

Provides automatic service registration with Nacos or Eureka
for Kubernetes and traditional deployments.

Supported registries:
- Nacos (Alibaba Cloud)
- Eureka (Netflix OSS)

Requirements:
    For Nacos: pip install nacos-sdk-python

Example:
    >>> from harness.service.discovery import NacosServiceRegistry
    >>> registry = NacosServiceRegistry("nacos:8848")
    >>> await registry.register("harness-agent", "10.0.0.1", 8000)
    >>> # ... service runs ...
    >>> await registry.deregister("harness-agent", "10.0.0.1", 8000)
"""

from __future__ import annotations

import logging
import os
import socket
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ServiceInstance:
    """Service instance information."""

    service_name: str
    ip: str
    port: int
    metadata: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "serviceName": self.service_name,
            "ip": self.ip,
            "port": self.port,
            "metadata": self.metadata or {},
        }


class ServiceRegistry(ABC):
    """Abstract base class for service registries."""

    @abstractmethod
    async def register(self, instance: ServiceInstance) -> bool:
        """Register a service instance."""
        pass

    @abstractmethod
    async def deregister(self, instance: ServiceInstance) -> bool:
        """Deregister a service instance."""
        pass

    @abstractmethod
    async def heartbeat(self, instance: ServiceInstance) -> bool:
        """Send heartbeat for a service instance."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the registry connection."""
        pass


class NacosServiceRegistry(ServiceRegistry):
    """
    Nacos service registry integration.

    Nacos is the preferred service discovery for Spring Cloud Alibaba.

    Example:
        >>> registry = NacosServiceRegistry("nacos:8848")
        >>> instance = ServiceInstance(
        ...     service_name="harness-agent",
        ...     ip="10.0.0.1",
        ...     port=8000,
        ...     metadata={"version": "1.0.0"}
        ... )
        >>> await registry.register(instance)
    """

    def __init__(
        self,
        server_addresses: str = "localhost:8848",
        namespace: str = "",
        username: str = "",
        password: str = "",
        group_name: str = "DEFAULT_GROUP",
    ):
        self.server_addresses = server_addresses
        self.namespace = namespace
        self.username = username
        self.password = password
        self.group_name = group_name
        self._client: Any = None

    def _get_client(self):
        """Get or create Nacos client."""
        if self._client is None:
            try:
                import nacos

                self._client = nacos.NacosClient(
                    self.server_addresses,
                    namespace=self.namespace,
                    username=self.username,
                    password=self.password,
                )
            except ImportError:
                raise ImportError(
                    "Nacos SDK is required. Install with: pip install nacos-sdk-python"
                ) from None
        return self._client

    async def register(self, instance: ServiceInstance) -> bool:
        """Register a service instance with Nacos."""
        try:
            client = self._get_client()
            client.add_naming_instance(
                service_name=instance.service_name,
                ip=instance.ip,
                port=instance.port,
                group_name=self.group_name,
                metadata=instance.metadata or {},
            )
            logger.info(
                f"Registered service {instance.service_name} "
                f"at {instance.ip}:{instance.port} with Nacos"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to register with Nacos: {e}")
            return False

    async def deregister(self, instance: ServiceInstance) -> bool:
        """Deregister a service instance from Nacos."""
        try:
            client = self._get_client()
            client.remove_naming_instance(
                service_name=instance.service_name,
                ip=instance.ip,
                port=instance.port,
                group_name=self.group_name,
            )
            logger.info(f"Deregistered service {instance.service_name} from Nacos")
            return True
        except Exception as e:
            logger.error(f"Failed to deregister from Nacos: {e}")
            return False

    async def heartbeat(self, instance: ServiceInstance) -> bool:
        """Send heartbeat to Nacos."""
        try:
            client = self._get_client()
            client.send_heartbeat(
                service_name=instance.service_name,
                ip=instance.ip,
                port=instance.port,
                group_name=self.group_name,
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send heartbeat to Nacos: {e}")
            return False

    async def close(self) -> None:
        """Close the Nacos client."""
        # Nacos client doesn't have a close method
        self._client = None


class EurekaServiceRegistry(ServiceRegistry):
    """
    Eureka service registry integration.

    Eureka is the traditional service discovery for Spring Cloud Netflix.

    Note: This is a basic implementation using HTTP API.
    For production, consider using the official Eureka client.

    Example:
        >>> registry = EurekaServiceRegistry("http://eureka:8761")
        >>> instance = ServiceInstance(
        ...     service_name="harness-agent",
        ...     ip="10.0.0.1",
        ...     port=8000,
        ... )
        >>> await registry.register(instance)
    """

    def __init__(self, eureka_server: str = "http://localhost:8761"):
        self.eureka_server = eureka_server.rstrip("/")
        self._session: Any = None

    async def _get_session(self):
        """Get or create HTTP session."""
        if self._session is None:
            try:
                import aiohttp

                self._session = aiohttp.ClientSession()
            except ImportError:
                raise ImportError(
                    "aiohttp is required for Eureka integration. Install with: pip install aiohttp"
                ) from None
        return self._session

    async def register(self, instance: ServiceInstance) -> bool:
        """Register a service instance with Eureka."""
        try:
            session = await self._get_session()

            # Eureka registration payload
            payload = {
                "instance": {
                    "app": instance.service_name.upper(),
                    "ipAddr": instance.ip,
                    "port": {
                        "$": instance.port,
                        "@enabled": True,
                    },
                    "status": "UP",
                    "metadata": instance.metadata or {},
                }
            }

            url = f"{self.eureka_server}/eureka/apps/{instance.service_name.upper()}"
            async with session.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status in (204, 200):
                    logger.info(
                        f"Registered service {instance.service_name} "
                        f"at {instance.ip}:{instance.port} with Eureka"
                    )
                    return True
                else:
                    logger.error(f"Eureka registration failed: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Failed to register with Eureka: {e}")
            return False

    async def deregister(self, instance: ServiceInstance) -> bool:
        """Deregister a service instance from Eureka."""
        try:
            session = await self._get_session()

            url = (
                f"{self.eureka_server}/eureka/apps/"
                f"{instance.service_name.upper()}/{instance.ip}:{instance.port}"
            )
            async with session.delete(url) as response:
                if response.status in (200, 204, 404):
                    logger.info(f"Deregistered service {instance.service_name} from Eureka")
                    return True
                else:
                    logger.error(f"Eureka deregistration failed: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Failed to deregister from Eureka: {e}")
            return False

    async def heartbeat(self, instance: ServiceInstance) -> bool:
        """Send heartbeat to Eureka."""
        try:
            session = await self._get_session()

            url = (
                f"{self.eureka_server}/eureka/apps/"
                f"{instance.service_name.upper()}/{instance.ip}:{instance.port}"
            )
            async with session.put(url) as response:
                return response.status in (200, 204)

        except Exception as e:
            logger.error(f"Failed to send heartbeat to Eureka: {e}")
            return False

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None


def get_pod_ip() -> str:
    """
    Get the Pod IP in Kubernetes environment.

    In K8s, socket.gethostbyname() may return 127.0.0.1 or the wrong IP.
    Use the POD_IP environment variable instead.

    Returns:
        Pod IP address
    """
    # K8s injects POD_IP environment variable
    pod_ip = os.getenv("POD_IP")
    if pod_ip:
        return pod_ip

    # Fallback to hostname resolution
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "127.0.0.1"


def get_service_instance(
    service_name: str = "harness-agent",
    port: int = 8000,
    metadata: dict[str, str] | None = None,
) -> ServiceInstance:
    """
    Create a service instance with auto-detected IP.

    Args:
        service_name: Service name for registration
        port: Service port
        metadata: Optional metadata

    Returns:
        ServiceInstance with auto-detected IP
    """
    ip = get_pod_ip()

    default_metadata = {
        "version": os.getenv("SERVICE_VERSION", "1.0.0"),
        "preserved.register.source": "PYTHON",
    }

    if metadata:
        default_metadata.update(metadata)

    return ServiceInstance(
        service_name=service_name,
        ip=ip,
        port=port,
        metadata=default_metadata,
    )


# Check what's available
try:
    import nacos  # noqa: F401

    NACOS_AVAILABLE = True
except ImportError:
    NACOS_AVAILABLE = False

# aiohttp is already a dependency, so Eureka should work
EUREKA_AVAILABLE = True
