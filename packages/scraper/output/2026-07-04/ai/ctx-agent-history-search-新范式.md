# ctx — Agent History Search 新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首个"Agent 历史搜索"概念，定义了 Agent Session Memory 新类别 |
| 采用广度 | ☆☆☆☆/5 | 支持 Claude Code、Codex、Cursor、Pi、OpenCode、Antigravity、Factory AI Droid、Copilot CLI 共 8+ 主流 Agent |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年7月 Show HN 首发 |
| 社区热度 | ☆☆☆/5 | Show HN 64分，解决 Agent 开发核心痛点 |
| **总体判断** | ✅ 新范式 | Agent 会话记忆的本地搜索引擎，解决"Agent 每次从零开始"的根本问题 |

## 技术定义 (What)

ctx 是一个开源 CLI 工具，用于在本地快速搜索过去所有编码 Agent 的会话历史。它将 Claude Code、Codex、Cursor 等 Agent 的本地日志索引到 SQLite 数据库中，让当前和未来的 Agent 能够检索之前的讨论、决策、失败尝试、命令和测试结果——比原始日志搜索节省 50 倍 token。

## 行业痛点 (Why)

编码 Agent 每次启动都从零开始。它们可以检查当前代码仓库，但无法恢复之前工作中的讨论、决策、失败尝试、命令和测试结果。这些历史会话中包含大量有价值的上下文：决策理由、约束条件、被拒绝的方案、bug 调查过程等。Agent 重复犯错、重复探索，浪费大量 token 和时间。

## 旧范式 vs 新范式

- **旧做法**：Agent 每次会话从零开始，无法访问历史上下文；或使用向量数据库/知识图谱存储压缩摘要，丢失原始决策链和失败记录
- **新做法**：将所有 Agent 会话日志结构化索引到本地 SQLite，通过会话-事件-元数据三层模型实现高效检索，Agent 可精确引用历史决策来源

## 生产力影响 (How)

1. **避免重复探索**：Agent 可搜索之前失败的方法，不再重复踩坑
2. **50x token 节省**：结构化检索返回精确定位的历史片段，而非原始日志全文
3. **跨 Agent 上下文传递**：Claude Code 的发现可被 Codex 后续会话检索
4. **决策溯源**：每个结果附带 ctx ID，可追溯到原始会话的具体事件

## 采用成本

- **时间**：5 分钟安装 + `ctx setup` 自动索引所有本地 Agent 历史
- **金钱**：完全免费，开源 MIT 协议
- **学习曲线**：极低，`ctx search "关键词"` 即可使用，支持 Agent Skill 自动集成
- **依赖**：Rust 编写，单二进制文件，无需后台服务、API Key 或云服务

## 采用案例

- **Claude Code 用户**：搜索之前会话中的重构决策，避免重复讨论
- **Codex 用户**：检索之前失败的迁移方案，直接跳过已知死路
- **Cursor 用户**：跨会话恢复 bug 调查上下文，继续未完成的排查
- **多 Agent 工作流**：一个 Agent 的发现自动对其他 Agent 可检索

## 风险/局限

- **隐私风险**：本地索引保留完整 transcript 文本（包括路径和密钥形状的字符串），复制输出前需审查
- **仅本地**：不支持远程/团队共享历史（设计选择，非缺陷）
- **依赖 Agent 本地日志**：如果 Agent 不持久化本地历史，ctx 无法索引
- **早期项目**：pre-1.0，API 可能变化

## 核心线索

- GitHub：https://github.com/ctxrs/ctx
- 官网：https://ctx.rs
- 首发来源：Show HN (2026年7月)
- 发布时间：2026年7月
- 当前状态：活跃 / 早期快速增长
- 技术栈：Rust + SQLite
- 支持 Agent：Claude Code, Codex, Cursor, Pi, OpenCode, Antigravity/Gemini CLI, Factory AI Droid, Copilot CLI