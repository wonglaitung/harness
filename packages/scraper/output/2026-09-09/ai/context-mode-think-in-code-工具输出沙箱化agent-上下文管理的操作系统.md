# Context Mode — Think-in-Code + Tool Output Sandboxing

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首创"Think-in-Code"强制范式 + 工具输出沙箱化 + 会话连续性的三位一体方案 |
| 采用广度 | ☆☆☆☆/5 | 已被 Microsoft、Google、Meta、Amazon、NVIDIA、Stripe 等 17+ 企业团队使用 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年9月初首发，HN 登顶 #1 |
| 社区热度 | ☆☆☆☆☆/5 | HN 570+ 分 #1，GitHub 652★/天，Discord 社区活跃 |
| **总体判断** | ✅ | **新范式 —— Agent 时代的"上下文操作系统"** |

## 技术定义 (What)

Context Mode 是一个 MCP Server，从四个维度解决 Agent 上下文窗口问题：
1. **工具输出沙箱化**：MCP 工具调用返回的原始数据不进入上下文窗口，98% 压缩（315KB → 5.4KB）
2. **会话连续性**：文件编辑、git 操作、任务状态通过 SQLite + FTS5 持久化，会话压缩时不会丢失记忆
3. **Think-in-Code**：强制 LLM 用代码分析数据而非将原始数据载入上下文——「模型是代码生成器，不是数据处理器」
4. **路由执行**：通过 PreToolUse/PostToolUse hooks 自动拦截 17 个平台的工具调用

## 行业痛点 (Why)

1M token 上下文窗口仍然不够用：每个 Playwright 快照 56KB，20 个 GitHub issue 59KB，30 分钟就消耗 40% 上下文。传统方案（对话压缩）导致 agent「失忆」——忘记正在编辑的文件、进行中的任务。

## 旧范式 vs 新范式
- **旧做法**：工具输出直接进上下文 → 上下文膨胀 → 压缩对话 → Agent 失忆
- **新做法**：工具输出进沙箱 → LLM 写代码分析数据 → 仅结果进上下文 → 事件索引进 FTS5 → 按需检索

## 生产力影响 (How)

- **Token 节省 98%**：一次 `ctx_execute()` 替代 47 次 `Read()`，700KB → 3.6KB
- **跨会话连续性**：Agent 不会因 `/clear` 丢失项目状态
- **Think-in-Code** 范式改变了 LLM 的使用方式：从"阅读-理解"变为"写代码-执行-读结果"

## 采用成本
- 安装：一行命令，免费开源
- 学习曲线：低（自动 hooks，无需手动操作）
- 兼容：Claude Code、Gemini CLI、Codex、Cursor、Windsurf、OpenCode 等 17 个平台

## 风险/局限
- 依赖 MCP 协议生态，非 MCP 工具无沙箱保护
- Think-in-Code 范式需要 Agent 具备代码生成能力（弱模型可能不适用）
- 社区仍在早期，长期维护待观察

## 核心线索
- GitHub：https://github.com/mksglu/context-mode
- HN 讨论：https://news.ycombinator.com/item?id=47193064（570+ 分，#1）
- 发布时间：2026年9月
- 当前状态：活跃（npm 持续更新）
- npm：https://www.npmjs.com/package/context-mode