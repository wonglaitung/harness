# LLM Wiki：持久化增量 Wiki 知识管理新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ★★★★★ | 首次将"增量构建持久化 Wiki"作为替代 RAG 的正式范式——知识编译一次、持续更新，而非每次查询重新推导 |
| 采用广度 | ★★★ | Karpathy 原创方法论背书；MCP Server + Agent Skill 支持 Claude Code/Codex；Obsidian 兼容 |
| 时间新鲜 | ★★★★ | 基于 Karpathy 2025年 llm-wiki 模式的全功能实现，持续活跃开发中 |
| 社区热度 | ★★★★ | GitHub 181⭐/天 trending，TypeScript #1 daily；自带 MCP Server、Agent Skill、HTTP API 生态 |
| **总体判断** | ✅ | **新范式 — "Wiki-as-Knowledge" 取代 "RAG-as-Knowledge"** |

## 技术定义 (What)
LLM Wiki 是一个跨平台桌面应用，让 LLM 增量构建并维护持久化 Wiki——而非每次查询重新检索（RAG）。知识编译一次后持续更新，形成结构化、可追溯、可图谱化的个人知识库。

## 行业痛点 (Why)
RAG 每次查询都从零检索，浪费 token、缺乏知识结构化、无法追溯来源。LLM Wiki 将"一次性 RAG"升级为"增量知识工程"——知识不断积累、链接、演化为图谱。

## 旧范式 vs 新范式
- **旧做法**：RAG——每次查询 embed→检索→生成，知识随用随丢，无结构化积累
- **新做法**：LLM 增量构建 Wiki——Ingest→分析→生成Wiki页面→链接→图谱，知识一次编译、持续复用

## 生产力影响 (How)
- Token 成本大幅降低——已处理文档无需重复分析
- 知识可追溯——每页 Wiki 标记来源文档（sources[] 字段）
- 知识图谱发现——Louvain 社区检测自动发现知识聚类、surprising connections、knowledge gaps
- Obsidian 兼容——Wiki 目录可直接作为 Obsidian Vault 打开

## 采用成本
- 桌面应用免费安装
- 需要 LLM API key（任意兼容 OpenAI 的提供商）
- 本地运行，数据不外传
- 学习成本低——三步：导入文档→AI构建Wiki→查询/浏览

## 采用案例
- **个人知识管理**：研究论文 → 结构化 Wiki + 知识图谱
- **企业知识库**：内部文档 → 可追溯 Wiki + Deep Research
- **学习辅助**：教材/笔记 → 交叉引用概念 Wiki

## 风险/局限
- 依赖 LLM 质量——模型能力直接影响 Wiki 质量
- 大型源文档 ingest 可能消耗较多 token
- 仍需人工 review（系统有 Lint/Review 机制）
- 知识图谱质量依赖于 wikilinks 准确性

## 核心线索
- GitHub：https://github.com/nashsu/llm_wiki
- 首发来源：Karpathy llm-wiki.md 模式（2025），本项目为全功能桌面实现
- 当前状态：活跃开发中
- 技术栈：TypeScript/Electron + Rust 后端 + LanceDB 向量搜索