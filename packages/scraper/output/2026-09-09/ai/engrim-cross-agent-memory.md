# Engrim — Universal Cross-Agent Episodic Memory

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首创"瑞士记忆"概念——跨模型跨Agent的持久化记忆解耦层，语言无关 |
| 采用广度 | ☆☆☆/5 | 支持 Google Antigravity、Claude Code、Cursor、Codex、Windsurf 全平台 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年9月初 Show HN（90分），v1.3.0 |
| 社区热度 | ☆☆☆/5 | Show HN 90分，PyPI已发布，105次连续会话实证 |
| **总体判断** | ✅ | **新范式 —— Agent 记忆即基础设施，解耦项目智能与单一供应商** |

## 技术定义 (What)

Engrim 是一个本地优先的 SQLite 记忆引擎，为 AI Coding Agent 提供跨模型、跨平台的持久化 episodic memory。核心理念："模型是可替换的工具，项目的决策不应该是"。Agent 切换模型（Gemini→Claude→Codex 甚至在同一次会话中），项目上下文（架构决策、用户约束、进度状态）毫发无损地继承。

技术架构：SQLite FTS5（BM25 关键词搜索）+ model2vec 静态向量嵌入的混合检索 + Agent 来源追踪。

## 行业痛点 (Why)

1. **注意力稀释**：长上下文窗口（1M+ tokens）导致推理退化，成本按每轮对话翻倍
2. **供应商锁死**：每个 Agent 生态的记忆格式不互通，切换模型意味着"失忆"
3. **上下文浪费**：153,000 tokens 的工作量浓缩到 <1,000 tokens (<1%)，每次重启节省 99%+

## 旧范式 vs 新范式

- **旧做法**：依赖单一 Agent 的上下文窗口，切换模型就丢失全部上下文；或用复杂 RAG 管道跨会话恢复
- **新做法**：一个语言无关的 SQLite 文件存储"决策/事实/反馈/状态"等类型化记忆，Board-level hooks 自动在 SessionStart 时注入上下文、Stop 时持久化新决策

## 生产力影响 (How)

- **Continue-as-Clear 工作流**：用 `resume-pointer` 标签标记下一步任务，清空上下文后无缝恢复
- **跨模型零漂移**：从 Gemini→Claude→Cursor 切换，Agent 立即知道项目在做什么
- **实证数据**：105 次连续会话、50,000 行代码的交易系统中零回归、零上下文失忆

## 采用成本

- `pip install engrim` + `engrim setup`（自动检测已安装的 Agent 环境）
- 零依赖 MCP JSON-RPC 服务器
- 学习曲线极低：一个 CLI 命令，Agent 自动写记忆

## 采用案例

- **算法交易系统**（自报）：153,000+ tokens 工作浓缩到 <1,000 tokens；跨 Google Antigravity / Claude Code / Cursor 无缝切换

## 风险/局限

- 仅处理"显式类型化记忆"（决策/事实/反馈），不替代全上下文的细粒度检索
- 依赖 Agent 主动调用 `engrim_add` 工具（已在 hooks 中自动化，但覆盖率非 100%）
- 向量嵌入使用静态 `model2vec`（无需 GPU，但语义精度低于大模型 embedding）

## 核心线索

- GitHub：https://github.com/timgordontg/engrim
- PyPI：https://pypi.org/project/engrim/
- 首发来源：Show HN (2026-09)
- 发布时间：2026年9月
- 当前状态：活跃开发中（v1.3.0）