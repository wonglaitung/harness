# 06 - 部署指南

## 概述

本文档描述 Harness Cloud 的部署方式，包括本地开发、Docker Compose 和 Kubernetes。

## 本地开发

### 前置条件

- Python 3.10+
- Node.js 18+
- Docker

### 启动步骤

```bash
# 1. 安装 Python 依赖
cd packages/cloud
uv sync

# 2. 启动 Agent（开发模式）
uv run uvicorn harness_cloud.agent.main:app --reload --port 8000

# 3. 启动 Gateway（另一个终端）
uv run uvicorn harness_cloud.gateway.main:app --reload --port 8080

# 4. 启动前端（另一个终端）
cd frontend
npm install
npm run dev
```

### 环境变量

```bash
# .env
ANTHROPIC_API_KEY=your-api-key
JWT_SECRET=your-secret-key
REDIS_URL=redis://redis:6379
```

## 网络架构

### 双网络设计

Harness Cloud 使用两个独立的网络：

| 网络 | 用途 | 访问外网 |
|-----|------|---------|
| `cloud-net` | Gateway ↔ Redis 通信 | 否 |
| `harness-net` | Gateway ↔ Agent 通信 | 是（Agent 需要访问 LLM API） |

**Gateway 连接两个网络**：
- `cloud-net`: 连接 Redis（速率限制）
- `harness-net`: 连接 Agent 容器

**Agent 只连接 `harness-net`**：
- 可以访问外网 LLM API（OpenAI、Anthropic 等）
- 与 Redis 隔离（安全性）

### 网络配置

```yaml
networks:
  # Gateway-Redis 通信
  cloud-net:
    driver: bridge

  # Gateway-Agent 通信（非 internal，允许出站）
  agent-net:
    name: harness-net
    driver: bridge
    # 注意：不设置 internal=True，Agent 需要访问 LLM API
```

> ⚠️ **评审意见修复**：
> 1. Gateway 使用非 root 用户
> 2. docker.sock 只读挂载
> 3. 添加 MinIO 文件存储

### docker-compose.yml

```yaml
version: '3.8'

services:
  gateway:
    build:
      context: .
      dockerfile: docker/gateway.Dockerfile
    ports:
      - "8080:8080"
    environment:
      - JWT_SECRET=${JWT_SECRET}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - REDIS_URL=redis://redis:6379
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro  # 只读挂载
    depends_on:
      - redis
      - minio
    networks:
      - harness-net

  frontend:
    build:
      context: frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - gateway
    networks:
      - harness-net

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - harness-net

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    volumes:
      - minio-data:/data
    networks:
      - harness-net

networks:
  harness-net:
    driver: bridge

volumes:
  minio-data:
```

### 构建镜像

```bash
# 自动构建并启动（推荐）
cd packages/cloud
./scripts/build.sh

# build.sh 自动执行：
# 1. 检测当前用户 UID、用户名、docker 组 GID
# 2. 构建 harness-agent:latest 和 harness-gateway:latest
# 3. 启动 docker-compose up -d

# 手动构建（可选）
docker-compose build --no-cache
docker-compose up -d

# 查看日志
docker-compose logs -f gateway
```

## Dockerfile

### Agent Dockerfile

```dockerfile
# docker/agent.Dockerfile

FROM python:3.11-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安装 Harness SDK
COPY --from=harness-sdk-builder /dist /dist
RUN pip install /dist/harness_sdk-*.whl

# 安装 Agent
COPY src/harness_cloud /app/harness_cloud
RUN pip install fastapi uvicorn websockets pydantic

# 创建工作目录
RUN mkdir /workspace
WORKDIR /workspace

EXPOSE 8000

CMD ["uvicorn", "harness_cloud.agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Gateway Dockerfile

```dockerfile
# docker/gateway.Dockerfile

FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    docker-cli \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY src/harness_cloud /app/harness_cloud
RUN pip install fastapi uvicorn websockets docker pydantic pyjwt

EXPOSE 8080

CMD ["uvicorn", "harness_cloud.gateway.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

## Kubernetes

### Namespace

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: harness-cloud
```

### Gateway Deployment

```yaml
# k8s/gateway-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gateway
  namespace: harness-cloud
spec:
  replicas: 2
  selector:
    matchLabels:
      app: gateway
  template:
    metadata:
      labels:
        app: gateway
    spec:
      containers:
        - name: gateway
          image: harness-cloud/gateway:latest
          ports:
            - containerPort: 8080
          env:
            - name: JWT_SECRET
              valueFrom:
                secretKeyRef:
                  name: harness-secrets
                  key: jwt-secret
            - name: ANTHROPIC_API_KEY
              valueFrom:
                secretKeyRef:
                  name: harness-secrets
                  key: anthropic-api-key
          volumeMounts:
            - name: docker-socket
              mountPath: /var/run/docker.sock
      volumes:
        - name: docker-socket
          hostPath:
            path: /var/run/docker.sock
```

### Gateway Service

```yaml
# k8s/gateway-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: gateway
  namespace: harness-cloud
spec:
  selector:
    app: gateway
  ports:
    - port: 80
      targetPort: 8080
  type: LoadBalancer
```

### Secrets

```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: harness-secrets
  namespace: harness-cloud
type: Opaque
stringData:
  jwt-secret: your-jwt-secret
  anthropic-api-key: your-api-key
```

### 部署命令

```bash
# 创建命名空间
kubectl apply -f k8s/namespace.yaml

# 创建 Secrets
kubectl apply -f k8s/secrets.yaml

# 部署 Gateway
kubectl apply -f k8s/gateway-deployment.yaml
kubectl apply -f k8s/gateway-service.yaml

# 查看状态
kubectl get pods -n harness-cloud
kubectl get services -n harness-cloud
```

## 资源配置

### 容器资源限制

| 容器类型 | CPU | 内存 | 超时 |
|---------|-----|------|------|
| Agent | 2 核 | 4GB | 10 分钟 |
| Gateway | 1 核 | 2GB | - |
| Frontend | 0.5 核 | 512MB | - |

### Kubernetes 资源配置

```yaml
resources:
  requests:
    cpu: "500m"
    memory: "512Mi"
  limits:
    cpu: "2000m"
    memory: "4Gi"
```

## 监控

### 健康检查端点

| 服务 | 端点 | 响应 |
|------|------|------|
| Agent | `GET /health` | `{"status": "healthy"}` |
| Gateway | `GET /health` | `{"status": "healthy", "containers": 5}` |

### Prometheus 指标

```python
# 可选：添加 Prometheus 指标
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter('harness_requests_total', 'Total requests')
REQUEST_LATENCY = Histogram('harness_request_latency_seconds', 'Request latency')
```

## 安全配置

### 认证系统

**当前状态**：Gateway 处于测试模式，接受任意非空 JWT token。

**待开发**：
- [ ] JWT 认证系统
  - 用户注册/登录
  - Token 生成与验证
  - Token 刷新机制
  - Token 撤销（登出）

**临时方案**：在测试环境中，Gateway 接受任何非空 token：
```json
{"type": "auth", "token": "any-non-empty-string"}
```

> ⚠️ **警告**：生产部署前必须实现完整的 JWT 认证系统。

### HTTPS（生产环境）

```yaml
# 使用 cert-manager 配置 TLS
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: harness-cert
  namespace: harness-cloud
spec:
  secretName: harness-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
    - harness.example.com
```

### 网络策略

```yaml
# 限制容器间通信
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: harness-network-policy
  namespace: harness-cloud
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: gateway
  egress:
    - to:
        - podSelector: {}
```

## 故障排查

### 常见问题

1. **容器无法启动**
   ```bash
   # 检查镜像是否存在
   docker images | grep harness

   # 检查日志
   docker logs harness-<session-id>

   # 重新构建（代码修改后需要重建）
   ./scripts/build.sh
   ```

2. **Agent 无法访问 LLM API（DNS 解析失败）**
   ```bash
   # 检查网络是否为 internal（应该是 false）
   docker network inspect harness-net --format '{{.Internal}}'
   # 输出应该是: false

   # 如果是 true，删除网络并重启
   docker network rm harness-net
   docker-compose down
   docker-compose up -d
   ```

3. **WebSocket 连接失败**
   ```bash
   # 检查 Gateway 日志
   docker-compose logs gateway

   # 检查端口是否开放
   netstat -tlnp | grep 8080
   ```

4. **认证失败**
   ```bash
   # 检查 JWT Secret
   echo $JWT_SECRET
   
   # 验证 token
   jwt decode <your-token>
   ```

### 日志查看

```bash
# Docker Compose
docker-compose logs -f gateway
docker-compose logs -f frontend

# Kubernetes
kubectl logs -f deployment/gateway -n harness-cloud
```

## Kubernetes 演进路径（修订）

> ⚠️ **评审意见**：标准 K8s 集群可能没有 `docker.sock`，建议使用原生 K8s API。

### 容器管理器抽象接口

```python
# gateway/container_manager.py
from abc import ABC, abstractmethod


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


# Docker 环境
class DockerManager(ContainerManager):
    """Docker 环境实现"""
    # ... 现有实现


# K8s 环境
class K8sPodManager(ContainerManager):
    """Kubernetes 环境实现"""

    def __init__(self, namespace: str = "harness-cloud"):
        from kubernetes import client, config
        config.load_incluster_config()
        self.core_v1 = client.CoreV1Api()
        self.namespace = namespace

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
                        env=[
                            client.V1EnvVar(name="SESSION_ID", value=session_id),
                            client.V1EnvVar(name="USER_ID", value=user_id),
                        ],
                    )
                ],
                restart_policy="Never",
                # 网络隔离：使用 NetworkPolicy
            ),
        )

        self.core_v1.create_namespaced_pod(self.namespace, pod)

        # 等待 Pod 就绪并获取 IP
        # ...

        return ContainerInfo(
            container_id=pod_name,
            session_id=session_id,
            user_id=user_id,
            internal_ip=pod_ip,
        )

    async def destroy_container(self, session_id: str) -> bool:
        """删除 Pod"""
        try:
            self.core_v1.delete_namespaced_pod(
                f"harness-{session_id}",
                self.namespace,
            )
            return True
        except Exception:
            return False

    def get_container_url(self, session_id: str) -> str:
        """获取 Pod WebSocket URL"""
        pod_name = f"harness-{session_id}"
        return f"ws://{pod_name}.harness-cloud.svc.cluster.local:8000/ws/run"
```

### K8s NetworkPolicy（替代 Docker 内部网络）

> ⚠️ **重要**：`egress: []` 表示拒绝所有出站流量。`- {}` 是允许所有，这是常见的配置错误！

```yaml
# k8s/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: sandbox-isolation
  namespace: harness-cloud
spec:
  podSelector:
    matchLabels:
      app: harness-agent
  policyTypes:
    - Ingress
    - Egress
  ingress:
    # 只允许 Gateway 访问
    - from:
        - podSelector:
            matchLabels:
              app: gateway
      ports:
        - port: 8000
  egress: []  # 明确拒绝所有出站流量（空数组 = 拒绝所有）
```

### 环境选择

```python
# gateway/main.py
import os

def get_container_manager() -> ContainerManager:
    """根据环境选择容器管理器"""
    environment = os.getenv("HARNESS_ENV", "docker")

    if environment == "k8s":
        return K8sPodManager(namespace="harness-cloud")
    else:
        return DockerManager()


# 使用
container_manager = get_container_manager()
```

