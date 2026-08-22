# Graphify — Code-as-Knowledge-Graph 知识图谱编译器新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次提出"任意文件→知识图谱编译器"概念，将 AST 精确提取（确定性）+ LLM 语义推理（概率性）统一为 KNOWLEDGE GRAPH，且每条边标记置信度（EXTRACTED/INFERRED/AMBIGUOUS） |
| 采用广度 | ☆/5 | 新项目，但已有 worked examples 验证 |
| 时间新鲜 | ☆☆☆☆/5 | GitHub trending #1 当天 480 stars，首次发布 < 1 个月 |
| 社区热度 | ☆☆☆☆/5 | GitHub 480 stars/天，社区高度关注 Karpathy 级工作流需求 |
| **总体判断** | ✅ | **新范式 —— Code-as-Knowledge-Graph 知识编译** |

## 技术定义 (What)
Graphify 在 Agent 和代码库之间插入一个"知识图谱编译器层"。输入任意混合文件（代码、PDF、截图、白板照片），输出一个可查询的持久化知识图谱。核心技术：
- **tree-sitter AST 解析**：确定性地从代码中提取函数/类/依赖关系 → EXTRACTED 边
- **Claude vision + LLM**：从文档、图片、论文中提取概念和关系 → INFERRED 边
- **Leiden 社区检测**：自动发现概念簇
- **SHA256 缓存**：增量重跑，只处理变化的文件

## 行业痛点 (Why)
Andrej Karpathy 的工作流：把论文、推文、截图、笔记都丢进 `/raw` 文件夹，但没有任何工具能让 Agent 高效理解这些混合内容。传统 RAG 丢失结构关系，全量读取炸 token 预算。

## 旧范式 vs 新范式
- **旧做法**：Agent 逐文件 read → 受上下文窗口限制；或用向量检索 → 丢失代码间结构依赖
- **新做法**：一次性编译为知识图谱 → Agent 通过结构化 query 获取精确关系 + LLM 推理连接；图持久化跨 session 复用

## 生产力影响 (How)
- **Token 节省**：52 文件混合语料，查询 token 降低 **71.5x**
- **结构可见**：God nodes 找核心概念、Surprising connections 发现隐藏关联
- **零运维**：`--watch` 自动同步 + git hook 提交即更新
- **Agent 导航**：`--wiki` 生成 Markdown 索引，任何 Agent 都能遍历知识库

## 采用成本
- `pip install graphifyy && graphify install`
- 需要 Claude Code（使用 Skills 机制）
- 纯本地运行，无服务器费用
- 学习成本：一个命令 `/graphify .`

## 采用案例
- Karpathy repos + 5 papers + 4 images（52 文件）：71.5x token 节省
- graphify 自身源码 + Transformer 论文（4 文件）：5.4x token 节省
- httpx 库（6 文件）：提供结构清晰度价值

## 风险/局限
- 依赖 Claude API（图像和多模态提取需要付费 tokens）
- 大型代码库首次构建耗时（但增量更新解决）
- 当前仅支持 Claude Code Skills 机制（计划扩展其他 Agent）

##  核心线索
- GitHub：https://github.com/Graphify-Labs/graphify
- 首发来源：GitHub Trending #1
- 发布时间：2026-08 月
- 当前状态：活跃开发中（v1）