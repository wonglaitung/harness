# Semantica — Graph-Native Context Infrastructure：AI Agent 决策追溯新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首次提出「Context Graph」+「Decision Intelligence」双层架构：在 LLM/向量库下方放置确定性图推理层，每个决策都是第一类可查询对象 |
| 采用广度 | ☆☆/5 | 早期阶段，支持 Agno、CrewAI、MCP 集成，Databricks/Snowflake 原生连接器 |
| 时间新鲜 | ☆☆☆☆/5 | 2026年活跃开发中，Python GitHub 趋势榜前列 |
| 社区热度 | ☆☆☆/5 | GitHub 趋势榜日榜前列，有完整的 YouTube 演示和文档站 |
| **总体判断** | ✅ | **新范式 — Graph-Native Context Infrastructure / Decision Provenance** |

## 技术定义 (What)

Semantica 在 LLM、向量数据库和 Agent 框架**下方**放置一个**确定性图推理基础设施层**。它不依赖 LLM 来构建图、推理或溯源。核心创新：

- **Context Graph**：将 Agent 所知、所决策、所推理的一切构建为结构化、可查询的知识图谱
- **Decision Intelligence**：每个决策都是第一类对象——可追溯、可按先例搜索、可因果关联
- **W3C PROV-O 溯源**：每个事实都有完整的来源追溯链，可导出 JSON/CSV/RDF
- **多后端图存储**：RDF（Oxigraph/Blazegraph/Jena）和 LPG（Neo4j/FalkorDB/AGE/Neptune）均可替换

## 行业痛点 (Why)

当前 AI Agent 的核心问题：**决策黑箱**。向量数据库存的是 embedding 相似度而非语义，决策无法被审计。在金融、医疗、法律、国防等受监管领域，监管者问「AI 为什么做这个决定？」时，传统 RAG 系统无法给出满意答案。Semantica 填补了这个空白。

## 旧范式 vs 新范式

| 维度 | 旧范式（Vector DB + RAG） | 新范式（Semantica Context Graph） |
|------|--------------------------|----------------------------------|
| 召回方式 | Embedding 相似度 | 图遍历 + 语义搜索 |
| 决策历史 | 不存储 | 第一类可查询对象 |
| 溯源 | 无 | W3C PROV-O，源头链接 |
| 推理 | 黑箱（LLM内部） | 前向链/Rete/Datalog/SPARQL |
| 冲突检测 | 静默覆写 | 检测→标记→解决 |
| 时间旅行 | 不支持 | 时间点图快照 |
| 合规导出 | 无 | PROV-O/SHACL/OWL/RDF |

## 生产力影响 (How)

- **受监管行业 AI 部署**：首次让 Agent 决策可通过合规审计
- **冲突消解**：多源数据中矛盾事实被标记而非静默覆写
- **决策溯源**：审核追溯路径（例如：贷款审批 → 模型输入 → 数据源 → 政策规则）
- **Databricks/Snowflake 原生连接**：已有数据湖/仓中的表直接变图节点，无需额外导出

## 采用成本

- 学习曲线：需要理解 RDF/SPARQL/W3C PROV-O 等语义网标准
- 部署：`pip install semantica`，自托管，零厂商锁定
- 存储：支持嵌入式 Oxigraph（零依赖）到企业级 Neptune

## 采用案例

- **金融合规**：贷款审批 Agent 的每个决策都可追溯到具体数据源和政策规则
- **医疗**：诊断建议附带证据链和冲突标记
- **国防/政府**：自托管、可审计、不可篡改的决策追溯

## 风险/局限

- 图构建需要一定领域建模能力（Ontology 设计）
- 早期项目，生态不如 LangChain 成熟
- 对简单 CRUD 类 Agent 可能过度设计
- 图推理性能在大规模场景下需要验证

## 核心线索

- GitHub：https://github.com/semantica-agi/semantica
- 网站：https://getsemantica.ai/
- 首发来源：GitHub 趋势榜
- 发布时间：2026年活跃开发
- 当前状态：活跃 / 早期
- License：MIT