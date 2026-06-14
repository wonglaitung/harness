# HelixDB

## 技术定义 (What)
专为 AI 应用设计的图向量数据库，在单一平台中整合 graph、vector、KV、document 和 relational 数据模型。从零用 Rust 构建，支持 ACID 事务、高可用部署和对象存储后端。

## 行业痛点 (Why)
构建 AI 应用需要组合多种数据存储：应用数据库、向量数据库、图数据库、KV 缓存等。数据分散在多个系统中，缺乏统一查询接口，Agent 难以高效访问和关联企业知识。

## 旧范式 vs 新范式
- **旧做法**：组合 PostgreSQL（关系数据）、Pinecone/Weaviate（向量搜索）、Neo4j（图查询）、Redis（KV 缓存）等多个数据库，通过应用层编排查询。数据孤岛问题严重，运维成本高。
- **新做法**：使用单一数据库存储所有数据模型，提供统一查询 DSL。AI Agent 通过一个接口访问图关系、向量相似度、文档检索、键值存储，数据自动关联和索引。支持从本地开发到云原生部署的无缝迁移。

## 生产力影响 (How)
大幅简化 AI 应用的数据架构，减少数据库实例数量和运维复杂度。Graph + Vector 组合特别适合知识图谱 RAG 场景。提供 helix chef 一键生成应用骨架，加速原型开发。

## 采用成本
安装简单（curl 安装 CLI），提供 TypeScript 和 Rust SDK。学习成本中等，需要理解图查询和向量搜索概念。Cloud 版本提供托管服务，本地开发支持内存和磁盘模式。

## 核心线索
- GitHub：https://github.com/HelixDB/helix-db
- 来源：https://github.com/HelixDB/helix-db
- 发布时间：2026-06-14
