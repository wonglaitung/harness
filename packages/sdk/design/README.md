# Harness SDK 设计文档

本目录包含 Harness SDK 的设计文档，记录尚未实现或正在开发中的功能设计。

## 文档列表

| 文档 | 状态 | 说明 |
|------|------|------|
| [loop-engineering.md](loop-engineering.md) | 部分实现 | Loop Engineering 总览 |
| [phase2-automations.md](phase2-automations.md) | ✅ 已实现 | Phase 2: 触发器系统 |
| [phase3-worktrees.md](phase3-worktrees.md) | ✅ 已实现 | Phase 3: 并行隔离执行 |
| [phase4-connectors.md](phase4-connectors.md) | ✅ 已实现 | Phase 4: 外部系统集成 |
| [phase5-orchestrator.md](phase5-orchestrator.md) | ✅ 已实现 | Phase 5: 统一编排 API |

## Loop Engineering 实现状态

| Phase | 组件 | 状态 | 核心功能 |
|-------|------|------|----------|
| Phase 1 | Goal Verifier | ✅ 已实现 | 目标驱动执行 + 验证器 |
| Phase 2 | Automations | ✅ 已实现 | Cron/Interval 触发 + 并发执行 |
| Phase 3 | Worktrees | ✅ 已实现 | Git worktree 隔离 + 并行执行 |
| Phase 4 | Connectors | ✅ 已实现 | Webhook/Slack/GitHub 集成 |
| Phase 5 | Orchestrator | ✅ 已实现 | Workflow + Team 编排 |

## 状态定义

| 状态 | 说明 |
|------|------|
| ✅ 已实现 | 功能已完成，文档可移至 `docs/` |
| 📝 设计完成 | 设计文档已完成，待开发 |
| 设计阶段 | 正在规划设计，尚未开始实现 |
| 开发中 | 正在实现中 |

## 文档规范

设计文档应包含：

1. **背景** - 为什么需要这个功能
2. **目标** - 这个功能要解决什么问题
3. **架构设计** - 技术方案和模块划分
4. **API 设计** - 用户如何使用
5. **实施步骤** - 具体的开发计划
6. **风险与缓解** - 潜在问题和解决方案

## 与 docs/ 的区别

| 目录 | 内容 | 状态 |
|------|------|------|
| `docs/` | 已实现功能的用户文档 | 稳定 |
| `design/` | 设计文档、开发计划 | 迭代中 |

功能实现完成后，相关设计文档应整理为用户文档，移至 `docs/` 目录。
