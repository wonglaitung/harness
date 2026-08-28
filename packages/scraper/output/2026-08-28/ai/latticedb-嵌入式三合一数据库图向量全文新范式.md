# LatticeDB

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ⭐⭐⭐⭐/5 | 将图数据库、向量搜索、全文检索三者统一在一个嵌入式单文件引擎中 |
| 采用广度 | ⭐⭐/5 | 刚发布，Show HN 引发 182 分热议 |
| 时间新鲜 | ⭐⭐⭐⭐/5 | 2026年8月首次亮相 Show HN |
| 社区热度 | ⭐⭐⭐/5 | Show HN 182 points，多个语言 SDK（Python/TypeScript/Go）已备 |
| **总体判断** | ✅ | **新范式 — 嵌入式三合一数据引擎，重新定义本地 AI 数据基础设施** |

## 技术定义 (What)
LatticeDB 是一个嵌入式单文件图-向量-全文三合一数据库。在同一个查询语言中，可以同时进行图遍历（节点→边→节点）、HNSW 向量相似搜索、和 BM25 全文检索。类似 SQLite 的单文件零配置体验，但底层是属性图 + 向量索引 + 倒排索引的融合引擎。

## 行业痛点 (Why)
当前 AI 应用（尤其是 Agent 记忆和 Graph RAG）面临"三数据库问题"：
- 语义搜索用向量数据库（Pinecone/Qdrant）
- 关系查询用图数据库（Neo4j）
- 文本搜索用搜索引擎（Elasticsearch）
三个系统之间数据同步、查询组合、运维开销极大。LatticeDB 用一个文件解决三者。

## 旧范式 vs 新范式
- **旧做法**：Neo4j + Pinecone + Elasticsearch，三套系统独立运维，跨系统查询需应用层拼接
- **新做法**：一个单文件嵌入式数据库，一条 Cypher 查询同时完成图遍历+向量搜索+全文检索

## 生产力影响 (How)
- **零运维**：单文件、零配置，类似 SQLite 体验
- **统一查询**：一个 Cypher 语句完成三种搜索，无需应用层数据拼接
- **极低延迟**：0.13μs 节点查找、0.83ms 百万向量搜索（100% 召回）
- **本地优先**：无需服务器，Agent 可本地运行完整数据栈

## 采用成本
- 学习曲线低（Cypher 语法 + 熟悉 SQLite 概念即可）
- Python `pip install latticedb`，TypeScript `npm install @hajewski/latticedb`
- 由 Zig 编写，性能卓越，Rust/Go/Python/TS 都有绑定

## 采用案例
- **Agent Memory**：LLM agent 用单一数据库管理对话图、语义记忆和全文搜索
- **Graph RAG**：知识图谱 + 向量检索 + 文本搜索的 RAG 管道一体化
- **本地知识工具**：Obsidian 类工具的图+语义后端

## 风险/局限
- 单机单写入模型，不适合分布式场景
- 目前使用 `hash_embed` 为占位嵌入，生产需接入真实 embedding 模型
- 项目早期，生态和稳定性待验证

## 核心线索
- GitHub：https://github.com/jeffhajewski/latticedb
- 首发来源：Show HN（2026年8月）
- 发布时间：2026-08
- 当前状态：活跃开发中