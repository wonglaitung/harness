# Apache Maka — Log is the Runtime：Agent 事件溯源运行时

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ★★★★★/5 | 首次将事件溯源（Event Sourcing）模式引入 AI Agent 运行时，"Log is the Runtime" 是全新架构命题 |
| 采用广度 | ☆☆/5 | Apache 孵化器项目，刚发布早期版本 |
| 时间新鲜 | ★★★★★/5 | 首次公开发布：2026年8月（GitHub Releases 第一个公开版本） |
| 社区热度 | ★★★☆/5 | GitHub trending TypeScript No.1，Apache 基金会背书 |
| **总体判断** | ✅ | **新范式 — Agent 运行时架构创新** |

## 技术定义 (What)
Apache Maka 是一个 local-first AI Agent 工作空间。核心创新在于 **"Log is the Runtime"** 架构：模型消息、Tool Call、Tool Result、权限决策、终止事件全部以 append-only 事件日志的形式记录。会话、UI、模型上下文、恢复操作都是对该事件日志的投影（projection），而非独立的存储结构。

## 行业痛点 (Why)
- **Agent 会话不可恢复**：当前 Agent 工具的对话历史难以精确重放，无法审计
- **上下文≠历史**：Tool Result 裁剪和 LLM 压缩改变了模型看到的内容，但不是以证据保留的方式
- **执行权分散**：UI、CLI、Eval 各自维护执行状态，没有统一权威来源
- **合规需求**：企业级 Agent 需要可审计的执行追踪

## 旧范式 vs 新范式
- **旧做法**：Agent 工具将消息存在对话数组里，压缩/裁剪后历史直接丢失；工具执行结果与 UI 状态耦合
- **新做法**：Runtime Event Log 作为唯一权威来源，所有表象（UI、context window、eval）都是对日志的物化视图；Tool Result 裁剪不影响证据保留

## 生产力影响 (How)
- **完整审计追踪**：任何时候都可以回溯 Agent 每一步做什么、为什么
- **会话恢复**：opt-in 安全边界恢复，崩溃后可从日志精确重放
- **统一执行权**：Desktop/TUI/CLI/Eval 共享同一个 Runtime Host，行为一致
- **分支与重试**：从任意 Turn 创建分支 session，实验不同决策路径

## 采用成本
免费开源（Apache 2.0）。macOS 桌面版提供签名 DMG 直接安装。需 Node.js 22.19+、ripgrep。自行配置模型 API。Windows 预览版未签名。

## 采用案例
- Apache 基金会官方孵化项目（incubating）
- 适合需要审计追踪的企业 Agent 部署场景

## 风险/局限
- 仍在活跃开发中，数据格式和 CLI 可能变化
- 仅 macOS Apple Silicon 桌面版为正式发布；Intel Mac/Windows/Linux 不支持
- 旧版会话历史不迁移（数据丢失边界明确声明）
- Tool 副作用不明确时的协调（Phase 3）尚未实现

## 核心线索
- GitHub：https://github.com/apache/maka
- HN 来源：GitHub Trending TypeScript
- 发布时间：2026年8月（首个公开 release）
- 当前状态：活跃开发中，Apache 孵化器项目