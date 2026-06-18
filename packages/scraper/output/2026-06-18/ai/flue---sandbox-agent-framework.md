# Flue - Sandbox Agent Framework

## 技术定义 (What)
Flue 是一个可编程的 TypeScript Agent Harness 框架，不是传统 SDK，而是提供完整的 Agent 运行环境：会话、工具、技能、文件系统访问和安全沙盒。它让任何模型都能获得真正自主工作所需的上下文和环境，支持本地 CLI 运行或部署到云端运行时。

## 行业痛点 (Why)
传统 LLM API 调用只能构建简单的聊天机器人和脚本任务，无法处理需要跨会话保持状态、访问文件系统、运行命令的复杂自主工作。Claude Code 和 Codex 展示了真正自主 Agent 的可能性，但开发者缺乏构建这类 Agent 的标准化框架。

## 旧范式 vs 新范式
- **旧做法**：使用原始 LLM API 调用构建 Agent，需要自己实现会话管理、工具调用、错误恢复、沙盒隔离等基础设施，每次都要从零开始。
- **新做法**：使用 Flue 的 Harness 架构，通过声明式配置组装 Agent 所需的全部组件：model、tools、skills、sandbox、instructions，框架自动处理会话持久化、工具调用、沙盒隔离、可观测性等复杂逻辑。

## 生产力影响 (How)
开发者可以快速构建生产级自主 Agent，无需重复实现基础设施代码。支持 Workflows（结构化自动化）、Subagents（专家委托）、Durable Execution（失败恢复）等高级特性，大幅降低 Agent 开发门槛。

## 采用成本
需要 Node.js 环境，学习 TypeScript Harness 架构。提供 CLI 快速启动，支持多种部署平台（Cloudflare Workers、GitHub Actions、Render 等）。采用成本较低，主要是学习曲线。

## 核心线索
- GitHub：https://github.com/withastro/flue
- 来源：https://github.com/trending/typescript
- 发布时间：2026-06-18
