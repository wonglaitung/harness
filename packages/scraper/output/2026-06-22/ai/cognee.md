# Cognee

## 技术定义 (What)
开源的 AI 记忆平台，为 Agent 提供跨会话的持久化长期记忆。通过向量嵌入、知识图谱推理和认知科学驱动的本体生成，让 Agent 能够记忆、连接和推理。

## 行业痛点 (Why)
当前 Agent 缺乏持久化记忆，每次会话从零开始。RAG 系统只能检索相似文本，无法构建关系网络。知识图谱需要人工构建，难以自动化。

## 旧范式 vs 新范式
- **旧做法**：使用向量数据库（Pinecone、Weaviate）存储嵌入，或手动构建知识图谱。记忆限于单一会话，无法跨会话学习和积累。
- **新做法**：Cognee 提供 `remember/recall/forget/improve` 四个操作。自动从非结构化数据构建知识图谱，结合向量搜索和图推理。支持多租户隔离、审计追踪、跨 Agent 知识共享。已有 Claude Code 插件和 OpenClaw 插件。

## 生产力影响 (How)
让 Agent 从"无记忆工具"进化为"可学习员工"。Agent 可以记住用户偏好、积累领域知识、从错误中学习。适用于 AI 员工、长期助手、企业知识库等场景。

## 采用成本
需要 Python 3.10-3.14，配置 LLM API 密钥。提供 CLI、API、MCP Server、Docker 多种部署方式。学习曲线：1-2 小时掌握核心 API。

## 核心线索
- GitHub：https://github.com/topoteretes/cognee
- 来源：https://github.com/trending/python
- 发布时间：2026-06-22
