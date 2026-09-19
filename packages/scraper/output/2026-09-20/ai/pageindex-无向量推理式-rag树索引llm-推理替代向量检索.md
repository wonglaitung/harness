# PageIndex — Vectorless, Reasoning-based RAG

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆ | 明确命名"vectorless RAG"、"reasoning-based retrieval"，提出 similarity ≠ relevance 的核心论点 |
| 采用广度 | ☆☆ | 新项目，Trendshift badge，GitHub trending 40 stars/day |
| 时间新鲜 | ☆☆☆☆ | 2026年8月发布 SDK/Flash，Vectorless RAG 概念首次系统提出 |
| 社区热度 | ☆☆☆ | Python trending，Trendshift 榜 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)
PageIndex 用**层级树索引（tree index）替代向量索引**，让 LLM **在树上推理着检索**（agentically search），就像人类专家翻阅长报告时找到正确的章节。检索分两步：① 为文档生成树结构索引；② 用 LLM 推理搜索这棵树。

## 行业痛点 (Why)
向量 RAG 靠语义相似度检索，但 **similarity（相似）≠ relevance（相关）**。在金融报告、法律文书、法规文件等需要上下文理解、领域知识、多步推理的专业长文档上，相似度搜索既漏掉"相关但不相似"的内容，又返回"相似但不相关"的内容。

## 旧范式 vs 新范式
- **旧做法**：向量索引 + 语义相似度搜索 → opacity "vibe retrieval"（不可追溯）
- **新做法**：树索引 + LLM 推理搜索 → 可追溯到显式引用，全程上下文感知

## 生产力影响 (How)
- FinanceBench 达 **98.7% accuracy**（向量 RAG 仅 50%）
- 成本：原生 PDF 输入在 420 页时贵 16.6×，PageIndex 成本不随文档长度线性增长（只读推理到达的节点）
- 索引成本约 $0.001/页，本地可跑

## 采用成本
低：`pip install -U pageindex`，本地模式可用自己的 LLM key，无需向量库/切块

## 采用案例
- 金融文档 QA（FinanceBench 98.7%）
- 法律/法规检索、技术手册、医学文献、学术教材

## 风险/局限
- 查询阶段依赖强模型（chat 模型决定检索质量）
- 相对年轻，生态待成长

## 核心线索
- GitHub：https://github.com/VectifyAI/PageIndex
- 首发来源：https://pageindex.ai/blog/pageindex-intro
- 发布时间：2026年8月
- 当前状态：试验中/早期活跃