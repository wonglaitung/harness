# LLM Wiki — Persistent Incremental Wiki (Anti-RAG)

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首次将 Karpathy 的「LLM Wiki 模式」实现为全功能桌面应用，提出「反 RAG」范式：知识被编译一次并保持最新，而非每次查询重新推导 |
| 采用广度 | ☆☆/5 | 首发阶段，525⭐/天 |
| 时间新鲜 | ☆☆☆☆☆/5 | GitHub trending 2026-09-13，525 stars/day |
| 社区热度 | ☆☆☆☆/5 | GitHub 525 stars/day（TypeScript trending #1），多语言 README |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)

LLM Wiki 是一个跨平台桌面应用，将文档自动转化为有组织、互联的知识库。与传统的 RAG（每次查询从零检索→回答）不同，LLM Wiki 让 LLM **增量构建和维护一个持久 wiki**。核心基于 Karpathy 的 LLM Wiki 模式：三层架构（Raw Sources → Wiki → Schema），但做了重大扩展。

## 行业痛点 (Why)

RAG 每次查询都重新检索和推理，浪费 token 且丢失上下文。Agent 编码会话的决策和洞察在会话结束后消失。传统 wiki 需要人工维护，始终落后于文档。

## 旧范式 vs 新范式
- **旧做法**：RAG（检索增强生成）：每次查询重新检索文档片段，token 消耗大，上下文丢失；或人工维护 wiki/confluence，始终过时
- **新做法**：LLM 增量编译文档为持久 wiki 页面，知识只需编译一次。两步 Chain-of-Thought Ingest（分析→生成），SHA256 增量缓存，4-信号知识图谱（直接链接×3、源重叠×4、Adamic-Adar×1.5、类型亲和度），Louvain 社区检测

## 生产力影响 (How)
- 文档导入后自动构建知识图谱，交叉引用自动生成
- 知识图谱发现「意外连接」和「知识缺口」，支持一键 Deep Research
- 完全兼容 Obsidian，wiki 目录可直接作为 Obsidian vault 使用
- 内置 MCP Server + HTTP API，可被其他 Agent 调用

## 采用成本
免费开源桌面应用，支持 macOS/Windows/Linux。自带多种 LLM provider 支持。

## 采用案例
- 个人研究知识库：导入论文 PDF→自动构建概念图谱
- 团队文档 wiki：导入内部文档→持续更新的知识库
- Agent 记忆后端：通过 MCP Server 被 Claude Code/Codex 调用

## 风险/局限
- 依赖 LLM 质量，错误可能传播到 wiki
- 大型文档库的首次 ingest 时间长
- 无法处理纯二进制格式

## 核心线索
- GitHub：https://github.com/nashsu/llm_wiki
- 首发来源：GitHub Trending
- 发布时间：~2026-09
- 当前状态：活跃开发中（525⭐/天）