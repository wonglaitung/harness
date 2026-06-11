# Harness Cloud 文档

## 文档索引

| 文档 | 说明 |
|------|------|
| [01-overview.md](./01-overview.md) | 项目概述与架构总览 |
| [02-agent.md](./02-agent.md) | Agent 胶水层设计 |
| [03-gateway.md](./03-gateway.md) | 网关控制层设计 |
| [04-frontend.md](./04-frontend.md) | Vue 前端开发 |
| [05-messages.md](./05-messages.md) | WebSocket 消息协议 |
| [06-deployment.md](./06-deployment.md) | 部署指南 |

## 快速开始

### 架构概览

```
[浏览器 Vue] ←→ WebSocket ←→ [Gateway] ←→ [Docker 容器] ←→ [Harness SDK]
```

### 开发阶段

| 阶段 | 内容 | 时间 |
|------|------|------|
| Phase 1 | Agent MVP（容器内 SDK 执行） | 1-2 周 |
| Phase 2 | Gateway MVP（容器调度） | 3-4 周 |
| Phase 3 | Frontend MVP（Vue 界面） | 5-6 周 |

### 技术栈

- **后端**: Python 3.11 + FastAPI
- **前端**: Vue 3 + TypeScript + Vite
- **容器**: Docker
- **状态管理**: Pinia

## 相关资源

- [Harness SDK 文档](../../sdk/docs/)
- [桌面客户端文档](../../client/)
