# Apache Maka — Log is the Runtime：Agent 事件溯源运行时新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首次提出"Log is the Runtime"——Model messages、工具调用、工具结果、权限决策、终止事件全部记录为 append-only log，Agent 的状态完全由事件日志推导 |
| 采用广度 | ☆☆/5 | Apache 孵化中，尚未被外部项目大规模采用，但进入 Apache 孵化器本身是质量标准 |
| 时间新鲜 | ☆☆☆☆☆/5 | Apache 孵化器阶段，2026年进入活跃开发 |
| 社区热度 | ☆☆☆/5 | GitHub 趋势榜 TypeScript 日榜第一，Apache 品牌背书 |
| **总体判断** | ✅ | **新范式 — Log-is-the-Runtime / Agent 事件溯源架构** |

## 技术定义 (What)
Apache Maka 是一个 local-first 的 AI Agent 工作空间。其核心架构创新在于：**所有 Agent 行为——模型消息、工具调用、工具结果、权限决策、终止事件——被记录为 append-only 事件日志**。UI 和下一次模型调用只是该日志的"视图"，日志本身才是事实来源。这种架构类似数据库的 WAL（Write-Ahead Log）或事件溯源模式，Agent 可以从中断处恢复、分支、重新生成。

## 行业痛点 (Why)
- **Agent 黑箱**：当前 Agent 框架中，prompt 是瞬态的、对话历史不可靠、无法精确审计 Agent 做了什么
- **中断即丢失**：Agent 崩溃后无法恢复——没有持久化的事件记录
- **上下文膨胀**：Agent 携带超长对话历史导致 token 消耗巨大，但没有办法安全地裁剪

## 旧范式 vs 新范式
- **旧做法**：Agent 框架以"对话线程"为核心，聊天历史是唯一状态，prompt 瞬态丢弃，崩溃后无法恢复
- **新做法**：append-only event log 是可验证的事实来源，UI 和推理调用只是日志的投影；可以安全地从上下文裁剪旧工具输出（因为它们仍在日志中），崩溃后可从日志恢复

## 生产力影响 (How)
- **可审计性**：Agent 的每一步操作都有不可篡改的日志，适合企业合规场景
- **崩溃恢复**：Agent 运行中断后可以精确恢复
- **分支实验**：从任意时间点分叉 Agent 行为进行对比实验
- **上下文高效**：安全裁剪旧输出不丢失信息

## 采用成本
- 开源（Apache 2.0），完全本地运行
- 目前仅支持 macOS Apple Silicon，Windows 预览，Linux 尚未支持
- 需要自行配置模型（云 API 或本地模型）
- 学习曲线低：类似 IDE 的桌面应用体验

## 采用案例
- Desktop、TUI/CLI、Eval 三种入口共享同一 Runtime Host
- 支持多模型连接、流式输出、思考过程、权限控制
- 内置工具：Read、Write、Edit、Bash、Glob、Grep
- 可选：Computer Use 和 Catalog Skills

## 风险/局限
- Apache 孵化中，尚未发布正式 Release
- 平台支持有限（macOS 为主）
- 数据格式、CLI 命令仍可能变化
- 生态尚未建立，社区插件体系待发展

## 核心线索
- GitHub：https://github.com/apache/maka
- 来源：GitHub Trending（TypeScript 日榜 #1）
- 发布时间：2026年进入 Apache 孵化器
- 当前状态：活跃开发中（Apache 孵化器）