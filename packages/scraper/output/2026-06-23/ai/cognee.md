# Cognee

## 技术定义 (What)
Cognee 是开源的 AI Agent 记忆平台，结合知识图谱和向量嵌入，为 Agent 提供跨会话的持久化长期记忆。核心创新：**remember-recall-forget-improve 操作模型**、**会话记忆 + 永久知识图谱双通道**、**多模态数据摄取**（文档、图像、对话）。Agent 可在会话间保持上下文，从历史交互中学习。

## 行业痛点 (Why)
Agent 无状态，每次对话重新开始。RAG 无法处理复杂关系。知识图谱需要专业团队维护。企业知识分散在多个系统（文档、数据库、聊天记录），难以统一给 Agent 使用。

## 旧范式 vs 新范式
- **旧做法**：使用向量数据库（Pinecone/Weaviate）存储文档嵌入，或手动构建知识图谱。数据摄取、清洗、建模需大量工程工作。Agent 仅能检索，无法动态更新知识。
- **新做法**：自动化知识图谱：摄取任意格式数据 → 自动构建实体-关系图 → 向量化存储 → 智能检索（自动选择最佳搜索策略）。**会话记忆**（快速缓存，后台同步到图谱）+ **永久记忆**（知识图谱）。提供 MCP Server，Agent 可直接调用记忆操作。

## 生产力影响 (How)
快速构建企业知识库。支持多租户隔离、审计追踪、可观测性（OpenTelemetry）。已有 Claude Code 插件，Agent 可跨会话保持记忆。适用于企业知识管理、智能客服、个人助理等场景。

## 采用成本
**时间成本**：`pip install cognee` 即可使用。Docker 部署约 5 分钟。**金钱成本**：开源免费（Apache 2.0）。需要 LLM API key 和图数据库（Neo4j/PostgreSQL）。**学习成本**：4 个核心 API（remember/recall/forget/improve），易于集成。

## 核心线索
- GitHub：https://github.com/topoteretes/cognee
- 来源：https://github.com/trending/python
- 发布时间：2026-06-23
