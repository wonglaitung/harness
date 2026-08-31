# GitNexus：预计算关系智能 — AI Agent 代码上下文新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 提出"Precomputed Relational Intelligence"概念，在索引时预计算代码结构（聚类、调用链、置信度评分），而非运行时让 LLM 自行探索 |
| 采用广度 | ☆☆/5 | 已支持 Cursor、Claude Code、Codex、Antigravity、Windsurf 等主流 AI 编码工具 |
| 时间新鲜 | ☆☆☆☆/5 | 近期发布，正在快速迭代 |
| 社区热度 | ☆☆☆☆/5 | GitHub Trending 182 stars/day，TypeScript 日榜前列 |
| **总体判断** | ✅ | **新范式 — 代码知识图谱预计算** |

## 技术定义 (What)
GitNexus 是一个零服务器、纯客户端的代码智能引擎。它将任意代码仓库索引为交互式知识图谱，通过 17 个 MCP 工具暴露给 AI Agent——每个依赖、调用链、代码簇和执行流都被预计算，Agent 只需一次调用即可获得完整上下文。

## 行业痛点 (Why)
当前 AI 编码工具（Cursor、Claude Code 等）不了解代码库结构：编辑 `UserService.validate()` 时不知道有 47 个函数依赖其返回类型，导致破坏性修改。传统 Graph RAG 给 LLM 原始图边让它自行探索，需要 4-10 次查询才能理解一个函数。

## 旧范式 vs 新范式
- **旧做法**：Graph RAG 给 LLM 喂原始图边 → LLM 多次查询探索 → 可能遗漏关键依赖
- **新做法**：索引时预计算所有关系 → 单次 MCP 工具调用返回完整结构化上下文 → LLM 不会遗漏

## 生产力影响 (How)
- **可靠性**：AI 不再"遗漏"依赖关系，所有上下文已在工具响应中
- **Token 效率**：无需 10 次查询链理解一个函数
- **模型民主化**：小模型也能获得完整架构清晰度，因为工具做了重活

## 采用成本
- npm 全局安装：`npm install -g gitnexus`
- 索引现有仓库：`npx gitnexus analyze`
- 学习曲线：低，MCP 自动配置主流编辑器

## 采用案例
- **Cursor / Claude Code / Codex**：通过 MCP 直接集成，Agent 获得代码库架构全景
- **Web UI 模式**：浏览器中直接聊天探索任何 GitHub 仓库

## 风险/局限
- 大仓库索引可能消耗较多内存
- PolyForm Noncommercial 许可证限制商业使用
- 依赖 Tree-sitter 解析，部分语言支持有限

## 核心线索
- GitHub：https://github.com/abhigyanpatwari/GitNexus
- 首发来源：GitHub Trending
- 当前状态：活跃开发中