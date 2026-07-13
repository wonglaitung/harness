# Background Agents (Open-Inspect) — 后台自主编码Agent新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次系统化"后台Agent编码"——Agent在后台自主工作，人类专注其他事务 |
| 采用广度 | ☆☆/5 | 新项目，受Ramp Inspect启发，开源复现 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年7月新发布，GitHub日增233星 |
| 社区热度 | ☆☆☆/5 | GitHub trending，但HN/社区讨论尚少 |
| **总体判断** | ✅ | **新范式（早期）** |

## 技术定义 (What)
Open-Inspect 是一个开源的后台编码Agent系统。Agent在独立沙箱中自主工作，支持多入口触发（Web UI、Slack、GitHub PR、Linear Issue、Webhook、Cron定时任务），可并行派生子任务，完成后自动创建PR并归属到发起用户。

## 行业痛点 (Why)
当前编码Agent（Claude Code、Codex等）都是"前台模式"——人类必须盯着屏幕等待Agent完成。对于大型任务（重构、迁移、批量修复），开发者被绑定在Agent执行过程中，无法并行处理其他工作。

## 旧范式 vs 新范式
- **旧做法**：开发者启动Agent → 等待 → 审批 → 等待 → 循环。Agent是同步工具，人类是瓶颈。
- **新做法**：开发者派发任务给后台Agent → 继续其他工作 → Agent完成后自动提PR。Agent是异步协作者，人类是调度者。

## 生产力影响 (How)
- 开发者可同时派发多个独立任务给不同沙箱并行执行
- 支持Cron定时任务和Sentry告警触发，实现"自愈代码"
- 多人可实时协作同一沙箱（multiplayer sessions）
- PR自动归属到发起用户，保持代码审查链完整

## 采用成本
- 需部署Cloudflare Workers + Durable Objects + 沙箱后端（Modal/Daytona/OpenComputer）
- 单租户架构，需组织内部部署
- 配置GitHub App、Slack Bot、Linear Bot等集成

## 采用案例
- **Ramp Inspect**：企业内部后台Agent系统，Open-Inspect的开源灵感来源
- **开源社区**：GitHub日增233星，快速获得关注

## 风险/局限
- 单租户设计，不支持多组织隔离
- 所有用户共享GitHub App凭证，无细粒度权限控制
- 沙箱后端依赖第三方（Modal/Daytona），成本和可用性受制
- Agent自主操作可能产生意外代码变更，需PR审查流程兜底

## 核心线索
- GitHub：https://github.com/ColeMurray/background-agents
- 灵感来源：https://builders.ramp.com/post/why-we-built-our-background-agent
- 发布时间：2026年7月
- 当前状态：早期活跃开发