# 03 - 网关控制层

## 概述

Gateway 是 Harness Cloud 的统一入口，负责容器调度、消息路由和用户认证。

## 目录结构

```
src/harness_cloud/gateway/
├── __init__.py
├── main.py              # Gateway FastAPI 入口
├── container_manager.py # 容器管理抽象接口
├── docker_manager.py    # Docker 实现
├── tunnel.py            # WebSocket 隧道
├── auth.py              # JWT 认证
├── rate_limiter.py      # Redis 限流器
└── config.py            # Gateway 配置
```

## 容器管理器抽象接口（新增）

```python
# gateway/container_manager.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ContainerInfo:
    """运行时容器信息"""
    container_id: str
    session_id: str
    user_id: str
    internal_ip: str
    internal_port: int = 8000
    created_at: datetime
    last_activity: datetime


class ContainerManager(ABC):
    """容器管理器抽象接口"""

    @abstractmethod
    async def create_container(
        self,
        session_id: str,
        user_id: str,
        workspace_path: str | None = None,
    ) -> ContainerInfo:
        """创建沙箱容器"""
        pass

    @abstractmethod
    async def destroy_container(self, session_id: str) -> bool:
        """销毁容器"""
        pass

    @abstractmethod
    def get_container_url(self, session_id: str) -> str:
        """获取容器 WebSocket URL"""
        pass

    @abstractmethod
    def get_container(self, session_id: str) -> ContainerInfo | None:
        """获取容器信息"""
        pass
```

## DockerManager - 容器管理

### 容器配置

```python
@dataclass
class DockerContainerConfig:
    """容器资源配置"""
    
    image: str = "harness-agent:latest"
    cpu_quota: int = 200000      # 2 CPU (100000 per CPU)
    memory_limit: str = "4g"
    memory_swap: str = "4g"
    timeout_seconds: int = 600   # 10 分钟超时
    pids_limit: int = 100        # 进程数限制
    internal_network: str = "harness-net"
    read_only_root_fs: bool = True
    cap_drop: list[str] = ["ALL"]
```

### 容器信息

```python
@dataclass
class ContainerInfo:
    """运行时容器信息"""
    
    container_id: str
    session_id: str
    user_id: str
    internal_port: int = 8000
    created_at: datetime
    last_activity: datetime
    container: Container  # Docker SDK 对象
```

### DockerManager 类

```python
class DockerManager:
    """
    管理 Docker 容器生命周期
    
    功能：
    - 创建/销毁容器
    - 资源限制
    - 超时清理
    """
    
    def __init__(self, gateway_config: GatewayConfig | None = None):
        self.gateway_config = gateway_config or GatewayConfig()
        self.config = self.gateway_config.container_config
        self.client = docker.from_env()
        self._containers: dict[str, ContainerInfo] = {}
        self._cleanup_task: asyncio.Task | None = None
    
    async def start(self):
        """启动后台清理任务"""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def stop(self):
        """停止并清理所有容器"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        for info in list(self._containers.values()):
            await self.destroy_container(info.session_id)
```

### 创建容器

```python
async def create_container(
    self,
    session_id: str,
    user_id: str,
    workspace_path: str | None = None,
) -> ContainerInfo:
    """
    创建沙箱容器
    
    Args:
        session_id: 会话 ID
        user_id: 用户 ID
        workspace_path: 可选的工作目录挂载
    
    Returns:
        ContainerInfo 容器信息

    ⚠️ 评审意见修复：使用内部网络替代 network_mode="none"
    """
    volumes = {}
    if workspace_path:
        volumes[workspace_path] = {
            "bind": "/workspace",
            "mode": "rw",
        }

    # tmpfs 挂载（修复只读文件系统问题）
    tmpfs = {
        "/tmp": "size=100M,mode=1777",  # Python 临时文件
    }

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

        # 资源限制
        cpu_quota=self.config.cpu_quota,
        mem_limit=self.config.memory_limit,
        memswap_limit=self.config.memory_swap,
        pids_limit=self.config.pids_limit,

        # 网络配置（修订：使用内部网络）
        network=self.config.internal_network,

        # 安全加固
        security_opt=["no-new-privileges"],
        cap_drop=self.config.cap_drop,
        read_only=self.config.read_only_root_fs,

        remove=False,
    )

    # 获取容器 IP
    container.reload()
    networks = container.attrs["NetworkSettings"]["Networks"]
    internal_ip = networks[self.config.internal_network]["IPAddress"]

    info = ContainerInfo(
        container_id=container.id,
        session_id=session_id,
        user_id=user_id,
        internal_ip=internal_ip,
        container=container,
    )

    self._containers[session_id] = info
    return info
```

### 销毁容器

```python
async def destroy_container(self, session_id: str) -> bool:
    """销毁容器"""
    info = self._containers.pop(session_id, None)
    if not info:
        return False
    
    try:
        info.container.remove(force=True)
        return True
    except Exception:
        return False
```

### 超时清理

```python
async def _cleanup_loop(self):
    """定期清理过期容器"""
    while True:
        await asyncio.sleep(60)  # 每分钟检查
        
        now = datetime.now()
        expired = []
        
        for session_id, info in self._containers.items():
            age = (now - info.last_activity).total_seconds()
            if age > self.config.timeout_seconds:
                expired.append(session_id)
        
        for session_id in expired:
            await self.destroy_container(session_id)
```

## WebSocketTunnel - 消息隧道

### 类定义

```python
class WebSocketTunnel:
    """
    双向 WebSocket 隧道
    
    Frontend WebSocket <-> Gateway <-> Container WebSocket
    """
    
    def __init__(self, container_url: str):
        self.container_url = container_url
        self._frontend_ws: WebSocket | None = None
        self._container_ws: WebSocketClientProtocol | None = None
        self._running = False
```

### 建立隧道

```python
async def connect(self, frontend_ws: WebSocket):
    """
    建立双向隧道
    
    1. 连接容器内的 Agent
    2. 启动双向转发任务
    """
    self._frontend_ws = frontend_ws
    self._running = True
    
    # 连接容器
    container_ws_url = f"ws://{self.container_url}/ws/run"
    self._container_ws = await websockets.connect(container_ws_url)
    
    # 双向转发
    await asyncio.gather(
        self._forward_to_container(),
        self._forward_to_frontend(),
    )
```

### 转发消息

```python
async def _forward_to_container(self):
    """前端 → 容器"""
    try:
        while self._running:
            data = await self._frontend_ws.receive_text()
            await self._container_ws.send(data)
    except Exception:
        self._running = False

async def _forward_to_frontend(self):
    """容器 → 前端"""
    try:
        while self._running:
            data = await self._container_ws.recv()
            await self._frontend_ws.send_text(data)
    except Exception:
        self._running = False
```

## Auth - 用户认证

### JWT 验证

```python
from jose import jwt, JWTError
from datetime import datetime, timedelta
from pydantic import BaseModel

from harness_cloud.gateway.config import GatewayConfig


class User(BaseModel):
    """JWT 中的用户信息（注意：是 pydantic BaseModel，不是 dataclass）"""
    id: str
    username: str = ""
    roles: list[str] = []


def verify_token(token: str, config: GatewayConfig) -> User:
    """验证 JWT Token 并返回 User

    注意：测试模式下若 jwt_secret 为默认值，任意非空 token 都会被接受并返回匿名用户。
    """
    # 测试模式：默认 secret 下接受任意非空 token
    if config.jwt_secret == "change-me-in-production" and token:
        return User(id="anonymous", username="test-user", roles=["user"])

    try:
        payload = jwt.decode(
            token,
            config.jwt_secret,
            algorithms=[config.jwt_algorithm],
        )
        return User(
            id=payload["sub"],
            username=payload.get("username", ""),
            roles=payload.get("roles", []),
        )
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e
```

### 创建 Token

```python
def create_token(
    user_id: str,
    config: GatewayConfig,
    expires_minutes: int | None = None,
) -> str:
    """创建 JWT Token

    Args:
        user_id: 用户标识
        config: Gateway 配置（提供 jwt_secret / jwt_algorithm / jwt_expire_minutes）
        expires_minutes: Token 过期时间（默认取 config.jwt_expire_minutes）
    """
    expires = expires_minutes or config.jwt_expire_minutes
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=expires),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm)
```

## Gateway FastAPI 入口

### main.py

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from harness_cloud.gateway.config import GatewayConfig, Settings
from harness_cloud.gateway.docker_manager import DockerManager
from harness_cloud.gateway.container_manager import ContainerManager
from harness_cloud.gateway.rate_limiter import RedisRateLimiter
from harness_cloud.gateway.tunnel import WebSocketTunnel
from harness_cloud.gateway.auth import User, verify_token


# 配置
settings = Settings.from_env()
config = GatewayConfig(
    jwt_secret=settings.jwt_secret or config.jwt_secret,
    redis_url=settings.redis_url or config.redis_url,
    environment=settings.environment or config.environment,
)

# 全局管理器
container_manager: ContainerManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    global container_manager
    container_manager = DockerManager(gateway_config=config)
    await container_manager.start()
    yield
    await container_manager.stop()


app = FastAPI(title="Harness Gateway", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### REST API 端点

```python
@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "containers": len(container_manager._containers),
    }


@app.post("/api/sessions")
async def create_session(user: User = Depends(lambda: None)):  # 占位鉴权
    """创建会话（MVP 阶段无鉴权）"""
    user_id = user.id if user else "anonymous"

    session_id = str(uuid.uuid4())[:8]

    info = await container_manager.create_container(
        session_id=session_id,
        user_id=user_id,
    )

    return {
        "session_id": session_id,
        "container_id": info.container_id[:12],
    }


@app.delete("/api/sessions/{session_id}")
async def destroy_session(
    session_id: str,
    user: User = Depends(lambda: None),
):
    """销毁会话"""
    user_id = user.id if user else "anonymous"
    info = container_manager.get_container(session_id)
    if not info:
        raise HTTPException(404, "Session not found")

    if info.user_id != user_id and user_id != "anonymous":
        raise HTTPException(403, "Not authorized")

    await container_manager.destroy_container(session_id)
    return {"status": "destroyed"}
```

### WebSocket 端点

```python
@app.websocket("/ws/session/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str):
    """
    会话 WebSocket 端点

    流程：
    1. 接受连接
    2. 等待首条 auth 消息（token 在消息体内，不在 URL）
    3. 验证 token（JWT）
    4. 验证会话所有权
    5. 建立隧道
    """
    await websocket.accept()

    # 网关层：等待首条 JWT 鉴权消息
    try:
        auth_msg = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
        auth_data = json.loads(auth_msg)
        if auth_data.get("type") != "auth":
            await websocket.close(code=4001, reason="Expected auth message")
            return
        token = auth_data.get("token", "")
    except asyncio.TimeoutError:
        await websocket.close(code=4001, reason="Auth timeout")
        return
    except json.JSONDecodeError:
        await websocket.close(code=4001, reason="Invalid auth message")
        return

    # 认证
    try:
        user = verify_token(token, config)
    except ValueError:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    # 获取容器
    info = container_manager.get_container(session_id)
    if not info:
        await websocket.close(code=4004, reason="Session not found")
        return

    if info.user_id != user.id and user.id != "anonymous":
        await websocket.close(code=4003, reason="Not authorized")
        return

    # 更新活动时间
    info.last_activity = datetime.now()

    # 建立隧道
    container_url = container_manager.get_container_url(session_id)
    tunnel = WebSocketTunnel(container_url)

    try:
        await tunnel.connect(websocket)
    except WebSocketDisconnect:
        pass
    finally:
        # WebSocket 断开后标记容器为 draining
        await container_manager.mark_draining(session_id)
```

## 配置

### config.py

```python
import os
from dataclasses import dataclass


@dataclass
class Settings:
    """
    从环境变量读取配置（HARNESS_ 前缀）

    - HARNESS_JWT_SECRET
    - HARNESS_REDIS_URL
    - HARNESS_ENVIRONMENT
    """

    jwt_secret: str | None = None
    redis_url: str | None = None
    environment: str | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            jwt_secret=os.getenv("HARNESS_JWT_SECRET"),
            redis_url=os.getenv("HARNESS_REDIS_URL"),
            environment=os.getenv("HARNESS_ENVIRONMENT"),
        )


settings = Settings.from_env()
```

## 启动命令

```bash
# 开发模式
uvicorn harness_cloud.gateway.main:app --reload

# 生产模式
uvicorn harness_cloud.gateway.main:app --host 0.0.0.0 --port 8080
```

## 安全加固（业界最佳实践）

### 容器隔离级别

> ⚠️ **重要**：Docker 容器共享宿主机内核，存在容器逃逸风险。2025年11月发现3个 runc 漏洞（CVE-2025-31133 等）。

| 隔离级别 | 技术 | 安全强度 | 适用场景 |
|---------|------|---------|---------|
| microVM | Firecracker, Kata Containers | 最强（硬件级） | 多租户、不可信代码 |
| gVisor | 用户空间内核 | 中强 | 计算密集型 |
| Hardened Container | seccomp + AppArmor | 基础 | 可信代码 |

**推荐**：MVP 阶段使用 Hardened Container，生产环境考虑 Kata/gVisor。

### Gateway 容器用户配置

Gateway 需要访问宿主机的 docker.sock，必须正确配置用户权限：

```dockerfile
# gateway.Dockerfile
FROM python:3.11-slim

# 创建 docker 组（GID 匹配宿主机 docker 组）
# 宿主机: getent group docker → docker:x:1001:marcowong
RUN groupadd -g 1001 docker && \
    useradd -m -u 1000 -G docker marcowong

# 安装 Docker CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    docker-cli \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY packages/cloud/src/harness_cloud /app/harness_cloud

# 安装依赖
RUN pip install --no-cache-dir fastapi uvicorn[standard] ...

# 设置目录权限
RUN chown -R marcowong:marcowong /app

# 以非 root 用户运行
USER marcowong

EXPOSE 8080
CMD ["uvicorn", "harness_cloud.gateway.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**权限原理**：

```
宿主机 docker.sock 权限：
srw-rw---- 1 root docker 0 /var/run/docker.sock
           │    └── gid=1001 (docker 组)

容器内用户配置：
uid=1000(marcowong) gid=1000(marcowong) groups=1001(docker)
                                      └── 可以读写 docker.sock
```

**为什么需要这样配置**：
1. docker.sock 的组权限是 `docker`（gid=1001）
2. 容器用户必须在该组内才能访问
3. 以 root 运行存在安全风险，非 root 用户是最佳实践

### 容器安全配置

```python
@dataclass
class DockerContainerConfig:
    """容器资源配置（含安全加固）"""
    
    image: str = "harness-agent:latest"
    cpu_quota: int = 200000
    memory_limit: str = "4g"
    memory_swap: str = "4g"
    timeout_seconds: int = 600
    
    # 安全加固
    pids_limit: int = 100           # 进程数限制
    internal_network: str = "harness-net"
    read_only_root_fs: bool = True  # 只读文件系统
    cap_drop: list[str] = ["ALL"]   # 移除所有能力
```

### 创建容器（安全加固版）

```python
async def create_container(
    self,
    session_id: str,
    user_id: str,
    workspace_path: str | None = None,
) -> ContainerInfo:
    """创建安全加固的沙箱容器"""
    volumes = {}
    if workspace_path:
        volumes[workspace_path] = {
            "bind": "/workspace",
            "mode": "rw",
        }
    
    container = self.client.containers.run(
        self.config.image,
        detach=True,
        name=f"harness-{session_id}",
        environment={
            "SESSION_ID": session_id,
            "USER_ID": user_id,
        },
        volumes=volumes,

        # 资源限制
        cpu_quota=self.config.cpu_quota,
        mem_limit=self.config.memory_limit,
        memswap_limit=self.config.memory_swap,
        pids_limit=self.config.pids_limit,  # 进程数限制

        # 网络隔离（ADR-008）：使用内部 bridge 网络 harness-net
        # 注意：不使用 internal=True，因为 Agent 需要访问外部 LLM API
        network=self.config.internal_network,

        # 安全加固
        security_opt=[
            "no-new-privileges",           # 禁止提权
            "seccomp=unconfined",          # 生产环境应配置具体 profile
        ],
        cap_drop=self.config.cap_drop,       # 移除能力
        read_only=self.config.read_only_root_fs,

        remove=False,
    )
    ...
```

### Rate Limiter（Redis 版本 - 修订）

> ⚠️ **评审意见修复**：原内存版本在多实例部署下会失效。改用 Redis 滑动窗口实现。

```python
# gateway/rate_limiter.py
import redis
import time


class RedisRateLimiter:
    """基于 Redis 的滑动窗口限流器"""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        max_requests: int = 100,
        window_seconds: int = 3600,
    ):
        self.redis = redis.from_url(redis_url)
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def check(self, user_id: str) -> bool:
        """检查是否超过限制（滑动窗口算法）"""
        key = f"rate_limit:{user_id}"
        now = time.time()
        window_start = now - self.window_seconds

        pipe = self.redis.pipeline()
        # 移除过期记录
        pipe.zremrangebyscore(key, 0, window_start)
        # 获取当前计数
        pipe.zcard(key)
        # 添加新记录
        pipe.zadd(key, {str(now): now})
        # 设置过期时间
        pipe.expire(key, self.window_seconds)

        results = pipe.execute()
        current_count = results[1]

        return current_count < self.max_requests


# 在 main.py 中使用
from harness_cloud.gateway.rate_limiter import RedisRateLimiter

rate_limiter = RedisRateLimiter(
    redis_url=settings.redis_url,
    max_requests=100,
    window_seconds=3600,
)

@app.post("/api/sessions")
async def create_session(user: User = Depends(lambda: None)):  # 占位鉴权
    if not rate_limiter.check(user.id):
        raise HTTPException(429, "Rate limit exceeded")
    ...
```

## 创建 Token（短期有效）

```python
def create_token(
    user_id: str,
    config: GatewayConfig,
    expires_minutes: int | None = None,
) -> str:
    """
    创建 JWT Token

    推荐：短期 Token（默认 config.jwt_expire_minutes=15分钟）+ 刷新机制
    """
    expires = expires_minutes or config.jwt_expire_minutes
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=expires),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm)


def refresh_token(token: str, config: GatewayConfig) -> str:
    """刷新 Token"""
    user = verify_token(token, config)
    return create_token(user.id, config)
```

## 安全检查清单（修订版）

### MVP 阶段必须

- [x] CPU/Memory 限制
- [x] **内部网络隔离**（`harness-net` 内部网络）
- [x] 超时自动清理
- [x] **进程数限制** (`pids_limit`)
- [x] **JWT 短期有效**（15分钟）
- [x] **Rate Limiter（Redis 版本）**
- [x] **Gateway 非 root 用户运行**
- [x] **只读文件系统 + tmpfs 挂载**

### 生产阶段建议

- [ ] seccomp profile
- [ ] AppArmor profile
- [ ] capability dropping
- [ ] 考虑 Kata Containers/gVisor
- [ ] Docker Rootless 模式
- [ ] Output Filtering（敏感数据过滤）

## K8sPodManager - Kubernetes 实现（设计提案，未实现）

> ⚠️ **NOT IMPLEMENTED (设计提案)**：`gateway/k8s_manager.py` 当前不存在，Gateway 仅提供 `DockerManager`（Docker 环境）。环境选择通过 `GatewayConfig.environment`（来自 `HARNESS_ENVIRONMENT`）完成，但代码中尚未实现 K8s 分支。
>
> 以下是参考设计，用于标准 K8s 集群，无需 docker.sock。

```python
# gateway/k8s_manager.py

from kubernetes import client, config
from harness_cloud.gateway.container_manager import ContainerManager, ContainerInfo


class K8sPodManager(ContainerManager):
    """Kubernetes 环境容器管理"""

    def __init__(self, namespace: str = "harness-cloud"):
        config.load_incluster_config()
        self.core_v1 = client.CoreV1Api()
        self.namespace = namespace
        self._containers: dict[str, ContainerInfo] = {}

    async def create_container(
        self,
        session_id: str,
        user_id: str,
        workspace_path: str | None = None,
    ) -> ContainerInfo:
        """创建 K8s Pod 作为沙箱"""
        pod_name = f"harness-{session_id}"

        pod = client.V1Pod(
            metadata=client.V1ObjectMeta(
                name=pod_name,
                labels={
                    "app": "harness-agent",
                    "session-id": session_id,
                    "user-id": user_id,
                },
            ),
            spec=client.V1PodSpec(
                containers=[
                    client.V1Container(
                        name="agent",
                        image="harness-agent:latest",
                        ports=[client.V1ContainerPort(container_port=8000)],
                        resources=client.V1ResourceRequirements(
                            requests={"cpu": "500m", "memory": "2Gi"},
                            limits={"cpu": "2000m", "memory": "4Gi"},
                        ),
                        # 健康检查（必须添加）
                        liveness_probe=client.V1Probe(
                            http_get=client.V1HTTPGetAction(path="/health", port=8000),
                            initial_delay_seconds=5,
                            period_seconds=10,
                        ),
                        readiness_probe=client.V1Probe(
                            http_get=client.V1HTTPGetAction(path="/health", port=8000),
                            initial_delay_seconds=2,
                            period_seconds=5,
                        ),
                    )
                ],
                restart_policy="Never",
            ),
        )

        self.core_v1.create_namespaced_pod(self.namespace, pod)
        # 等待 Pod 就绪并获取 IP...
        return ContainerInfo(container_id=pod_name, session_id=session_id, user_id=user_id, internal_ip=pod_ip)

    async def destroy_container(self, session_id: str) -> bool:
        try:
            self.core_v1.delete_namespaced_pod(f"harness-{session_id}", self.namespace)
            return True
        except Exception:
            return False

    def get_container_url(self, session_id: str) -> str:
        return f"ws://harness-{session_id}.{self.namespace}.svc.cluster.local:8000/ws/run"
```

## MinIO 文件存储（设计提案，未实现）

> ⚠️ **NOT IMPLEMENTED (设计提案)**：`gateway/file_storage.py` 当前不存在，MinIO 文件存储尚未实现。以下是参考设计，使用预签名 URL，前端直传 MinIO，避免大文件经过 Gateway 内存。

```python
# gateway/file_storage.py

from minio import Minio


class FileStorage:
    """MinIO 文件存储 - 支持预签名 URL"""

    def __init__(self, endpoint: str = "minio:9000", access_key: str = "minioadmin", secret_key: str = "minioadmin"):
        self.client = Minio(endpoint, access_key, secret_key, secure=False)
        self.bucket = "harness-files"
        self._ensure_bucket()

    def get_presigned_put_url(self, object_name: str, expires: int = 3600) -> str:
        """获取预签名上传 URL - 前端直接 PUT 到 MinIO"""
        return self.client.presigned_put_object(self.bucket, object_name, expires=expires)

    async def get_download_url(self, object_name: str, expires: int = 3600) -> str:
        """获取预签名下载 URL"""
        return self.client.presigned_get_object(self.bucket, object_name, expires=expires)
```

### API 端点

```python
@app.post("/api/files/presign-upload")
async def get_upload_url(filename: str, user: User = Depends(lambda: None)):  # 占位鉴权
    """获取预签名上传 URL（设计提案）"""
    user_id = user.id if user else "anonymous"
    object_name = f"{user_id}/{uuid.uuid4().hex[:8]}_{filename}"
    upload_url = file_storage.get_presigned_put_url(object_name)
    return {"upload_url": upload_url, "object_name": object_name}

@app.post("/api/files/presign-download")
async def get_download_url(object_name: str, user: User = Depends(lambda: None)):  # 占位鉴权
    """获取预签名下载 URL（设计提案）"""
    user_id = user.id if user else "anonymous"
    if not object_name.startswith(f"{user_id}/"):
        raise HTTPException(403, "Access denied")
    download_url = await file_storage.get_download_url(object_name)
    return {"download_url": download_url}
```

## WebSocket 鉴权方式

> **Gateway 层鉴权**：JWT Token 通过首条消息传递，避免 URL 参数泄露。
>
> **Agent 层鉴权**：Gateway 透传前端消息，Agent 负责 API Key 认证（auth-first 协议）。

```python
@app.websocket("/ws/session/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str):
    """
    会话 WebSocket 端点

    Gateway 负责 JWT 验证，然后透传所有消息到容器内的 Agent。
    Agent 负责 API Key 认证（auth-first 协议）。
    """
    await websocket.accept()

    # Gateway 层：等待首条 JWT 鉴权消息
    try:
        auth_msg = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
        auth_data = json.loads(auth_msg)
        if auth_data.get("type") != "auth":
            await websocket.close(code=4001, reason="Expected auth message")
            return
        token = auth_data.get("token", "")
    except asyncio.TimeoutError:
        await websocket.close(code=4001, reason="Auth timeout")
        return
    except json.JSONDecodeError:
        await websocket.close(code=4001, reason="Invalid auth message")
        return

    # 验证 JWT
    try:
        user = verify_token(token, config)
    except ValueError:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    # 验证会话所有权
    info = container_manager.get_container(session_id)
    if not info:
        await websocket.close(code=4004, reason="Session not found")
        return
    if info.user_id != user.id and user.id != "anonymous":
        await websocket.close(code=4003, reason="Not authorized")
        return

    # 建立隧道，透传所有后续消息（包括 Agent 的 auth 消息）
    container_url = container_manager.get_container_url(session_id)
    tunnel = WebSocketTunnel(container_url)
    await tunnel.connect(websocket)
```

## 验证测试

### 创建会话

> ⚠️ **注意**：Gateway 没有 `/api/auth/login` 路由。MVP 阶段 `/api/sessions` 使用占位鉴权（`Depends(lambda: None)`，无需 token），且 `verify_token` 在默认 `jwt_secret` 下接受任意非空 token 并返回匿名用户。

```bash
# 创建会话（MVP 阶段无需鉴权）
curl -X POST http://localhost:8080/api/sessions
# Response: {"session_id": "abc123", "container_id": "a1b2c3d4"}

# 健康检查
curl http://localhost:8080/health
# Response: {"status": "healthy", "containers": 1}

# 连接 WebSocket（Gateway 鉴权：首条消息携带 JWT）
wscat -c "ws://localhost:8080/ws/session/abc123"

# Gateway 鉴权（首条消息，type 必须为 "auth"）
> {"type": "auth", "token": "$TOKEN"}

# Agent 鉴权（API Key）
> {"type": "auth", "payload": {"api_key": "sk-ant-xxx", "provider": "anthropic"}}
< {"type": "auth_success", "payload": {"provider": "anthropic", "model": "claude-sonnet-4-6"}}

# 执行任务
> {"type": "run_request", "payload": {"prompt": "Hello"}}
```

### 资源限制验证

```bash
# 查看容器资源使用
docker stats harness-abc123

# 预期输出：
# CONTAINER     CPU %    MEM USAGE / LIMIT
# harness-abc   50%      512MiB / 4GiB

# 验证进程数限制
docker exec harness-abc123 cat /sys/fs/cgroup/pids/max
# 预期输出: 100
```

### Rate Limit 验证

```bash
# 连续请求直到触发限制（MVP 阶段匿名用户不触发限流）
for i in {1..110}; do
  curl -X POST http://localhost:8080/api/sessions
done

# 预期：第 101 次返回 429 Too Many Requests（已鉴权用户）
```

## 下一步

- [01-overview.md](./01-overview.md) - 了解 Cloud 整体架构
- [02-agent.md](./02-agent.md) - 了解 Agent 胶水层设计
- [06-deployment.md](./06-deployment.md) - 了解部署指南