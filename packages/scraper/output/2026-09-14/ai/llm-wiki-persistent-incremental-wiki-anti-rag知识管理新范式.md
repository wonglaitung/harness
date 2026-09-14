# LLM Wiki — 持久化增量 Wiki 知识管理新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 颠覆 RAG 范式：知识编译一次、持久化，而非每次查询重新检索。引入 purpose.md（Wiki 灵魂）、两步 Chain-of-Thought Ingest、4-Signal 知识图谱 + Louvain 社区发现 |
| 采用广度 | ☆☆☆/5 | GitHub trending 260 stars/day，基于 Karpathy llm-wiki 方法论 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026-09 trending，非常新 |
| 社区热度 | ☆☆☆☆/5 | GitHub trending TypeScript #1（260 stars/day），多个语言 README |
| **总体判断** | ✅ | **新范式** — 知识管理从"每次重算"走向"增量编译" |

## 技术定义 (What)

LLM Wiki 将文档转化为组织化、互联的知识库。与 RAG（每次查询重新检索和回答）不同，LLM Wiki **增量构建并维护持久化 Wiki**：知识编译一次，保持最新，不在每次查询时重新推导。

核心流程：两步 Chain-of-Thought Ingest → Step 1 LLM 分析文件（实体/概念/连接/矛盾）→ Step 2 LLM 生成 Wiki 页面（带 frontmatter、[[wikilink]] 交叉引用）。SHA256 增量缓存跳过未修改文件。

## 行业痛点 (Why)

RAG 的"每次从头检索+回答"模式存在根本缺陷：(1) 查询时计算成本高；(2) 跨文档关联丢失；(3) 知识无法结构化积累；(4) 每次回答质量不一致。LLM Wiki 把 LLM 当作"知识编译器"而非"检索器"。

## 旧范式 vs 新范式

- **旧做法**：RAG — 向量数据库 + 每次查询检索相关片段 + LLM 实时生成回答。知识无结构化持久状态。
- **新做法**：Incremental Wiki — LLM 读取源文件、分析结构、生成持久化 Wiki 页面。4-Signal 知识图谱（直接链接/源重叠/Adamic-Adar/类型亲和性）+ Louvain 社区发现自动发现知识集群。

## 生产力影响 (How)

- 从"搜索+阅读"转向"已编译的知识库直接问答"
- 自动发现"惊人连接"和"知识空白"
- Obsidian 兼容 — Wiki 目录可直接作为 Obsidian Vault 使用
- 内置 Deep Research：LLM 优化搜索主题 + 多查询 web 搜索 + 自动接入 Wiki

## 采用成本

免费开源，桌面应用跨平台。需自备 LLM API key（支持任意 OpenAI 兼容端点）。SHA256 缓存降低 token 消耗。内置场景模板（研究/阅读/个人成长/商业/通用）。

## 采用案例

- 研究场景：研究者导入论文集 → 自动构建互联知识图谱 → 发现跨论文的模式和矛盾
- 个人知识管理：导入 PDF、网页、笔记 → 持久化第二大脑 → Obsidian 中浏览和编辑

## 风险/局限

- 早期项目，UI/UX 仍在迭代中
- 依赖 LLM 质量（分析步骤可能产生幻觉）
- 对超大文档集合的可扩展性需验证
- 非 RAG 替代，而是互补范式

## 核心线索

- GitHub：https://github.com/nashsu/llm_wiki
- 方法论来源：Karpathy llm-wiki.md gist
- 发布时间：2026 年（GitHub trending 2026-09）
- 当前状态：活跃开发中