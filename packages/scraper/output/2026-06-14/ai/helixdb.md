# HelixDB

## 技术定义 (What)
专为 AI 应用设计的图+向量数据库，用 Rust 从零构建，支持知识图谱、AI 记忆、KV、文档和关系数据，提供单一平台替代多个数据库。

## 行业痛点 (Why)
构建 AI 应用需要多个数据库（关系数据库、向量数据库、图数据库），架构复杂，数据同步困难，运维成本高。

## 旧范式 vs 新范式
- **旧做法**：使用 PostgreSQL 存储结构化数据，Pinecone/Qdrant 存储向量，Neo4j 存储图关系，需要维护多个系统和数据同步层。
- **新做法**：单一数据库支持图+向量+KV+文档+关系数据，提供 Rust/TypeScript DSL 动态查询，支持 ACID 事务，无需构建中间层。

## 生产力影响 (How)
开发者可用一个数据库构建 RAG 应用、知识图谱、Agent 记忆系统，减少 60% 以上架构复杂度，降低运维成本。

## 采用成本
开源免费，提供本地开发环境和云端托管服务，CLI 一键安装，支持 Docker 部署。

## 核心线索
- GitHub：https://github.com/HelixDB/helix-db
- 来源：https://github.com/HelixDB/helix-db
- 发布时间：2026-06-14
