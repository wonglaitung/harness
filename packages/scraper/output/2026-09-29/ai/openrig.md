# OpenRig

## 技术定义 (What)
用 YAML 定义 Agent 团队（seats），一条命令同时启动 Claude Code 与 Codex 作为统一编排系统。引入"harness 包裹一个模型，rig 包裹你的 harnesses"的多层编排概念，将多个 AI 编码代理从零散终端会话变成有状态团队。

## 行业痛点 (Why)
多个编码 Agent（Claude Code、Codex）各自独立运行在终端里，没有团队编排、状态持久化或协作分工。

## 旧范式 vs 新范式
- **旧做法**：逐个打开终端运行单一编码 Agent，人工协调多个 Agent 间的协作。
- **新做法**：YAML 定义团队 + 一条命令启动，lead Agent 协调 specialists，任务队列、状态和上下文持久化在同一地址，跨 harness 的多 Agent 协作。

## 生产力影响 (How)
把异构编码 Agent（不同厂商 harness）封装成可复用团队，为 AI 编码引入"团队即基础设施"的组织化工作流。

## 采用成本
低：npm 安装 + Node.js 22/24 + tmux，需已认证的 Codex；无原生 Windows 支持。

## 核心线索
- GitHub：https://github.com/mvschwarz/openrig
- 来源：https://github.com/trending/typescript (734 stars today)
- 发布时间：2026-09-29
