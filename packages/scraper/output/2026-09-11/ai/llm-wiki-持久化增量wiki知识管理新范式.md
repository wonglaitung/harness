# LLM Wiki — 持久化增量Wiki知识管理新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 从"Stateless RAG"到"Persistent Incremental Wiki"的范式转换，定义了新的知识管理类别。基于Karpathy概念但实现了完整系统 |
| 采用广度 | ☆☆/5 | 94 stars，但已被多个Agent框架关注；内置MCP Server和Agent Skill，生态可扩展 |
| 时间新鲜 | ☆☆☆/5 | 基于Karpathy 2025年的llm-wiki概念，完整实现在2026年发布 |
| 社区热度 | ☆☆/5 | GitHub 94 stars今日，TypeScript trending上榜 |
| **总体判断** | ✅ | **新范式 — 知识管理从"检索"走向"编译+积累"** |

## 技术定义 (What)
LLM Wiki 将LLM的知识管理方式从传统的"检索-回答"(RAG)转变为"增量构建持久Wiki"。文档摄入通过两步CoT：Step 1 分析（提取实体、概念、关联）、Step 2 生成（创建Wiki页面、更新索引、标记交叉引用）。核心创新：知识只编译一次，持续维护——不是每次查询都重新推理。

## 行业痛点 (Why)
传统RAG的三个根本问题：
1. **无累积**：每次查询都是临时检索+生成，知识不沉淀
2. **无结构**：文档间隐含关系无法被发现和组织
3. **无演化**：新增文档无法自动更新已有知识结构

## 旧范式 vs 新范式
- **旧做法**：RAG（检索→拼凑上下文→LLM生成→丢弃）
- **新做法**：Wiki Ingest（分析→编译为结构化Wiki→持久化→增量更新→知识图谱）

## 生产力影响 (How)
- **知识图谱**：4信号相关性模型（直接链接×3、来源重叠×4、Adamic-Adar×1.5、类型亲和力）
- **社区发现**：Louvain算法自动发现知识聚类
- **知识缺口**：自动识别"令人惊讶的连接"和空白领域
- **Agent集成**：内置MCP Server + Agent Skill，可作为AI编程Agent的知识后端

## 采用成本
- 免费开源，跨平台桌面应用
- 本地运行，需LLM API key
- 场景模板降低上手门槛
- 与Obsidian完全兼容

## 采用案例
- 个人研究知识库管理
- 团队文档自动结构化
- Agent知识后端（通过MCP/Agent Skill）

## 风险/局限
- 依赖LLM质量，低质量模型可能导致知识提取不准确
- 社区尚小（94 stars），生态待验证
- 大型文档库的Wiki膨胀管理

## 核心线索
- GitHub：https://github.com/nashsu/llm_wiki
- 概念来源：Andrej Karpathy's llm-wiki pattern
- 发布时间：2026年
- 当前状态：活跃开发中