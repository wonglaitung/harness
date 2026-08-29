# LatticeDB — Embedded Property-Graph + Vector + Full-Text Database

## 技术定义 (What)
LatticeDB 是一个嵌入式单文件属性图数据库，在同一查询引擎中原生集成了图遍历（Cypher风格）、HNSW向量相似搜索和BM25全文检索。类似SQLite的零配置哲学——"Like SQLite but for graph databases"。一个文件、零服务器、零配置，专为Agent记忆、Graph RAG和本地知识工具设计。

## 行业痛点 (Why)
当前AI Agent的知识基础设施严重碎片化：向量搜索用Qdrant/Pinecone，图遍历用Neo4j/Neptune，全文搜索用Elasticsearch。三套系统、三种API、三次数据同步。对于本地Agent（比如Claude Code读取本地文件做RAG），部署三套数据库是不现实的。

## 旧范式 vs 新范式
- **旧做法**：旧范式：Agent记忆/知识管理需要部署和维护至少3套独立数据库系统（向量库+图库+全文检索引擎），各自独立部署、各自独立API、数据需要多次同步。本地优先的Agent工具面临"无数据库可用"的困境。
- **新做法**：新范式：一个文件、一个查询层、一个事件日志。在同一查询中同时进行图遍历（MATCH）、向量搜索（<=>）、全文搜索（@@）。例如"找到与查询向量相似的chunk，遍历到它的文档，再找到作者"。0.13μs节点查找，100万向量搜索0.83ms@100%召回。

## 生产力影响 (How)
消除Agent知识基础设施的部署负担。开发者在本地用pip install即获得完整的三合一知识引擎。对Graph RAG、Agent Memory、本地知识助手等场景，将部署复杂度从"三套数据库+同步层"降到"一个文件"。

## 采用成本
极低：pip install latticedb，单文件零配置。支持Python/TypeScript/Go/Java多语言绑定。学习成本为类Cypher查询语法。

## 核心线索
- GitHub：https://github.com/jeffhajewski/latticedb
- 来源：https://news.ycombinator.com/show
- 发布时间：2026-08-29
