# Flue

## 技术定义 (What)
可编程的 TypeScript Agent Harness 框架，为 Agent 提供会话、工具、技能、指令、文件系统访问和安全沙箱，使其能真正自主完成复杂任务。不是 SDK，而是完整的 Agent 运行时环境。

## 行业痛点 (Why)
现有 Agent 构建方式多为原始 LLM API 调用，缺乏持久化会话、安全沙箱、工具编排、技能复用等关键能力，难以构建真正自主的 Agent。

## 旧范式 vs 新范式
- **旧做法**：使用 LangChain/LlamaIndex 等 SDK 拼接工具，手动管理会话状态、错误恢复、权限控制，Agent 能力受限且难以扩展。
- **新做法**：声明式配置 Agent：模型 + 工具 + 技能 + 沙箱 + 指令，框架自动处理会话持久化、错误恢复、安全隔离、可观测性。支持子 Agent 委托、工作流编排、MCP 服务器连接。

## 生产力影响 (How)
开发者专注定义 Agent 能力而非基础设施；支持本地 CLI 运行或部署到 Cloudflare Workers/GitHub Actions/Render 等；内置 OpenTelemetry/Braintrust/Sentry 可观测性。

## 采用成本
中等：需学习 Flue 的 Agent 架构（会话/工具/技能/沙箱概念），但 TypeScript 类型系统提供良好开发体验。文档完善，支持多部署平台。

## 核心线索
- GitHub：https://github.com/withastro/flue
- 来源：https://github.com/trending/typescript
- 发布时间：2026-06-19
