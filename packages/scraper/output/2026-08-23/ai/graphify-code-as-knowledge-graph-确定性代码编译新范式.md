# Graphify — Code-as-Knowledge-Graph 确定性代码编译新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ⭐⭐⭐⭐⭐/5 | "Code-as-Knowledge-Graph" — 将代码库从"文本+向量"提升为"结构化知识图谱"。确定性 AST 解析替代概率性向量搜索，"每一条边都有语义解释"的核心设计 philosophy 颠覆了 RAG 范式 |
| 采用广度 | ⭐⭐⭐/5 | GitHub Trending Python #1，480 stars/天。已被集成到多个 Agent CLI 的 Skill 生态 |
| 时间新鲜 | ⭐⭐⭐⭐⭐/5 | 2026年8月发布，极新 |
| 社区热度 | ⭐⭐⭐⭐⭐/5 | GitHub Trending Python #1（480 stars/天），增长迅猛 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)

Graphify 是一个确定性代码知识图谱编译器。它以代码库的 AST 为输入（含文档、SQL Schema、配置文件、PDF），输出可查询的知识图谱。每个节点之间都有明确的语义边（调用、继承、配置依赖、数据流），Agent 通过图遍历获得精确的结构上下文。

核心理念：**不是"猜"关系，而是"编译"关系。**

## 行业痛点 (Why)

当前 AI Coding Agent 的最大瓶颈不是模型能力，而是**上下文质量**：

- RAG 用向量相似度"猜"哪些代码相关 → 经常返回不相关的片段
- Agent 理解不了模块间调用关系 → 修一个 Bug 引入三个新 Bug
- 大型代码库的结构信息完全丢失 → Agent 只能在局部文本中工作

## 旧范式 vs 新范式

| | 旧范式（RAG/向量搜索） | 新范式（Graphify） |
|---|---|---|
| 关系发现 | 概率性（向量相似度） | 确定性（AST 边） |
| 可追溯性 | "为什么返回这段代码？因为向量距离近" | "从 main() → handler → db.query 的调用链" |
| 跨文件理解 | 弱（每段独立嵌入） | 强（调用图天然跨文件） |
| Agent 能问的问题 | "找相似的代码" | "这个函数的调用者是谁？修改它影响哪些模块？" |
| 存储 | 向量数据库（非确定性） | 图数据库（可审计） |

## 生产力影响 (How)

- ** Debugging**：Agent 可以精确追溯 bug 的影响范围（从 bug 函数顺着调用图向下→影响的所有模块）
- **Refactoring**：重构前 Agent 能精确知道每个接口的调用者
- **Onboarding**：新人（或 Agent）通过知识图谱理解代码架构，而非逐个文件阅读
- **Security Audit**：追踪敏感数据从输入到输出的完整数据流路径

## 采用成本

- **安装**：`pip install graphify`，10 秒
- **运行**：本地确定性 AST 解析，无需 GPU 或 API
- **集成**：已支持 Claude Code、Cursor、Codex、Gemini CLI 的 `/graphify` Skill
- **学习曲线**：低（对 Agent 透明，Agent 自动使用）

## 采用案例

- **Claude Code 集成**：`/graphify` 命令一键生成项目知识图谱
- **Cursor 集成**：代码审查时提供结构上下文
- **Codex 集成**：大项目重构的结构化分析

## 风险/局限

- 依赖 AST 解析的语言覆盖（目前支持主流语言，小众语言覆盖率待验证）
- 超大型 monorepo 的图谱规模可能过大（需要增量编译策略）
- 需要 Agent 学会"何时查图谱 vs 何时读文件"

## 核心线索

- GitHub：https://github.com/Graphify-Labs/graphify
- 首发来源：GitHub Trending Python #1（2026-08-23）
- 发布时间：2026年8月
- 当前状态：活跃增长中（480 stars/天）