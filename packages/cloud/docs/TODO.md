# Harness Cloud 开发进度

> 最后更新: 2026-06-13

## 已完成功能

### Agent (容器内代理)

- [x] FastAPI WebSocket 端点 (`/ws/run`)
- [x] SDK Bridge - 连接 WebSocket 与 Harness SDK
- [x] 流式执行 (`asyncio.to_thread`)
- [x] 进度事件转换 (ProgressEvent → WebSocket 消息)
- [x] 心跳检测
- [x] 内存软限制
- [x] SessionSync 模块 (状态持久化)

### Gateway (网关控制层)

- [x] FastAPI 入口
- [x] DockerManager - Docker 容器管理
- [x] WebSocket Tunnel - 消息转发
- [x] JWT 认证 (测试模式，接受任意 token)
- [x] Redis Rate Limiter
- [x] 容器生命周期管理 (创建/销毁/超时清理)

### 部署

- [x] Docker Compose 配置
- [x] Agent Dockerfile (多阶段构建)
- [x] Gateway Dockerfile (非 root 用户)
- [x] build.sh (自动检测 UID/GID)
- [x] 内部网络隔离 (`harness-net`)

### 安全

- [x] 容器资源限制 (CPU/Memory/PIDs)
- [x] 只读文件系统 + tmpfs
- [x] 内部网络隔离
- [x] Gateway 非 root 用户运行
- [x] docker.sock 只读挂载

---

## 待开发功能

### 1. JWT 认证系统 (高优先级)

**当前状态**: Gateway 处于测试模式，接受任意非空 token。

**待开发**:
- [ ] 用户注册 API (`POST /api/auth/register`)
- [ ] 用户登录 API (`POST /api/auth/login`)
- [ ] Token 生成 (Access Token + Refresh Token)
- [ ] Token 验证中间件
- [ ] Token 刷新 API (`POST /api/auth/refresh`)
- [ ] Token 撤销/登出 API (`POST /api/auth/logout`)
- [ ] 用户数据库 (PostgreSQL 或 SQLite)

**参考**: `packages/cloud/docs/06-deployment.md` 安全配置部分

### 2. MinIO 文件存储 (中优先级)

**用途**: 用户上传文件到沙箱工作区

**待开发**:
- [ ] FileStorage 类 (`gateway/file_storage.py`)
- [ ] 预签名上传 API (`POST /api/files/presign-upload`)
- [ ] 预签名下载 API (`POST /api/files/presign-download`)
- [ ] docker-compose.yml 添加 MinIO 服务
- [ ] 前端直传实现

**参考**: `packages/cloud/docs/complete-design.md` 3.7 节

### 3. K8sPodManager (低优先级)

**用途**: Kubernetes 环境部署，替代 Docker

**待开发**:
- [ ] K8sPodManager 类 (`gateway/k8s_manager.py`)
- [ ] Kubernetes NetworkPolicy 配置
- [ ] 环境选择逻辑 (Docker vs K8s)

**参考**: `packages/cloud/docs/complete-design.md` 3.5 节

### 4. 断线重连 (中优先级)

**用途**: WebSocket 断线后恢复会话

**待开发**:
- [ ] `resume_request` 消息类型
- [ ] Agent 端恢复逻辑
- [ ] 前端重连策略

**参考**: `packages/cloud/docs/complete-design.md` 2.5 节

### 5. Vue 前端 (高优先级)

**待开发**:
- [ ] 项目初始化 (Vue 3 + TypeScript + Vite)
- [ ] WebSocket 客户端 (`composables/useWebSocket.ts`)
- [ ] ChatPanel 组件
- [ ] ToolDisplay 组件
- [ ] SettingsPanel 组件
- [ ] Pinia 状态管理

**参考**: `packages/cloud/docs/04-frontend.md`

### 6. 生产安全加固 (低优先级)

**待开发**:
- [ ] seccomp profile 配置
- [ ] AppArmor profile 配置
- [ ] 考虑 Kata Containers 或 gVisor

---

## 技术债务

1. **K8sManager 文档重复** - `complete-design.md` 中有代码重复段落
2. **测试覆盖** - 缺少单元测试和集成测试
3. **错误处理** - 需要更完善的错误码和错误消息

---

## 参考文档

- [complete-design.md](./complete-design.md) - 完整设计文档
- [06-deployment.md](./06-deployment.md) - 部署指南
