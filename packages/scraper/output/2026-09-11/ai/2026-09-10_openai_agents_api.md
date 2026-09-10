# OpenAI Agents API — Agent 基础设施即服务新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首次将 Agent 运行时（Harness）作为托管云服务提供，定义了"Agent Infrastructure as a Service"新类别 |
| 采用广度 | ☆☆☆/5 | 已有 9 个沙箱生态伙伴（Cloudflare、DigitalOcean、Modal、Vercel 等），处于公测阶段 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026-09-09 公开发布（公测），距今不足 1 天 |
| 社区热度 | ☆☆☆☆/5 | HN 首页热门讨论，Codex 生态已有数百万用户基础 |
| **总体判断** | ✅ | **新范式 — Agent 基础设施从自建走向托管服务** |

## 技术定义 (What)

OpenAI Agents API 是一个托管云服务，开发者通过单个 API 调用即可创建生产就绪的 AI Agent。它封装了 Codex Harness 的全部基础设施能力：上下文压缩（自动 compaction）、工具搜索与编排、多 Agent 并行协调、沙箱环境管理。

## 行业痛点 (Why)

当前构建生产级 Agent 需要开发者自行实现：上下文管理、工具编排、长时间运行可靠性、沙箱安全隔离、子 Agent 协调——这些都是极其复杂的分布式系统问题。每个团队都在重复造轮子。

## 旧范式 vs 新范式

- **旧做法**：开发者自建 Agent 基础设施——自己实现 compaction 逻辑、工具搜索、多 Agent 编排、沙箱管理
- **新做法**：单个 API 调用，指定任务+模型+工具+环境，OpenAI 托管全部基础设施

## 生产力影响 (How)

- 将 Agent 开发从"数周的基础设施搭建"缩短为"分钟级的 API 调用"
- 自动获得 Codex 级别的上下文管理优化，无需自行实现
- 版本化的 Harness 与模型同步升级，模型越强 Harness 越智能

## 采用成本

- **零额外费用**：仅按 token 和工具使用量计费
- **学习曲线**：低（标准 REST API）
- **迁移成本**：从自建基础设施迁移需重构

## 采用案例

- 沙箱生态伙伴：Blaxel、Cloudflare、Daytona、DigitalOcean、E2B、Modal、Oracle、Runloop、Vercel
- Harness 开源：https://github.com/openai/codex

## 风险/局限

- 公测阶段，API 可能变动
- 供应商锁定风险（Harness 虽开源，但托管服务深度绑定 OpenAI）
- 不适合极端定制化的 Agent 场景

## 核心线索

- 官方博客：https://openai.com/index/introducing-the-agents-api
- API 文档：https://developers.openai.com/api/docs/guides/agents-api/overview
- 发布时间：2026-09-09
- 当前状态：公测（Public Beta）