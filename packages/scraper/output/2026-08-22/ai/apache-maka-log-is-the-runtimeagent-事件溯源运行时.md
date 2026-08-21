# Apache Maka — Log is the Runtime：Agent 事件溯源运行时新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首次将数据库"事件溯源"模式完整应用于 Agent 运行时：模型消息、工具调用、工具结果、权限决策、终止事件均为 append-only 日志，Session/UI/Context/Recovery 均为日志的投影 |
| 采用广度 | ☆☆/5 | Apache 孵化项目，早期发布（仅 macOS），尚未被广泛集成 |
| 时间新鲜 | ☆☆☆☆☆/5 | 首次公开 macOS 桌面构建（2026-08 前后），处于活跃开发 |
| 社区热度 | ☆☆/5 | GitHub 141⭐/天（TypeScript trending），Apache 品牌背书 |
| **总体判断** | ✅ | **新范式** — 事件溯源+Agent 运行时的融合开辟了 Agent 可审计、可恢复、可分支的全新架构 |

## 技术定义 (What)
Apache Maka 将 Agent 的所有执行状态建模为**仅追加事件日志（Runtime Event Log）**。模型消息、工具调用、工具结果、权限决策、终止事件全部进入日志。会话（Session）、UI、模型上下文（Context）、启动恢复（Recovery）都是该日志的**投影（projection）**——不是独立的存储副本，而是从事件流派生的视图。

核心架构：
```
Desktop / TUI / CLI → Runtime Host → SessionManager → AgentRun
                                        ↓
                                   Model + Tool Runtime → Runtime Event Log
                                        ↓
                                   Context / Session / UI projections
```

## 行业痛点 (Why)
当前 AI Agent 工具（Claude Code、Cursor、Copilot 等）的会话状态是**黑箱**：消息历史、工具调用、中间决策混在一起，无法审计、无法回放、无法从任意点恢复。断电/崩溃后只能从头开始。更致命的是——无法对 Agent 行为做可重现评估。

## 旧范式 vs 新范式
- **旧做法**：Agent 运行时状态散落在内存、数据库、文件系统和模型上下文中，各组件各自维护状态，无法统一溯源
- **新做法**：所有事件进入单一 append-only 日志。Session 是日志的投影。Context 是日志的投影（可裁剪、可压缩但原始证据不丢失）。Recovery 是日志的重放。Eval 是日志的交叉对比

## 生产力影响 (How)
1. **可审计 Agent**：每个工具调用、权限决策都有完整事件链，安全/合规审计不再是黑箱
2. **可恢复会话**：崩溃后从日志恢复完整状态，不丢任何决策
3. **可分支探索**：从任意 Turn 分支出新的 AgentRun，对比不同策略
4. **可重现评估**：Eval 基于同一事件日志对比不同模型/配置，结果完全可复现
5. **Context ≠ History**：裁剪/压缩上下文不影响原始证据（日志保留完整记录）

## 采用成本
- 仅支持 macOS Apple Silicon（早期发布限制）
- 需自配模型连接（不捆绑模型账户）
- 学习曲线中等：需理解事件溯源和投影的概念
- 无 Computer Use 功能（首个公开构建未包含）

## 风险/局限
- Apache 孵化阶段，API 和数据格式可能变更
- 仅 macOS，跨平台支持待完善
- 性能特性未大规模验证（事件日志在长期运行中的存储增长）
- 与现有 Agent 工具生态的互操作性待建立

## 核心线索
- GitHub：https://github.com/apache/maka
- 架构文档：ARCHITECTURE.md（含 6 篇双语深度解析）
- 当前状态：Apache 孵化中，活跃开发
- 发布形式：npm 包 + Electron 桌面应用