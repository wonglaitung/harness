# Semantica

## 技术定义 (What)
Semantica 是一个图原生（Graph-Native）的 AI Agent 基础设施层，位于 LLM、向量数据库和 Agent 框架之下。它将 Agent 的上下文、决策和知识建模为结构化知识图谱（Context Graph），内建 W3C PROV-O 溯源、确定性推理引擎（前向链、Rete 网络、Datalog、SPARQL）和 SHACL 合规约束。一句话：AI Agent 的 Palantir — 让 Agent 的每个决策都可追溯、可审计、可解释。

## 行业痛点 (Why)
传统 Agent 是黑箱：embedding 存储的是"相似度"而非"含义"，决策不可审计。在金融、医疗、法律等受监管行业，"AI 为什么做出这个决定？" 无法回答就等同于违规。向量数据库 + RAG 没有溯源、没有冲突检测、没有时间旅行能力。

## 旧范式 vs 新范式
- **旧做法**：Agent 记忆 = 向量数据库 + 聊天历史。决策不可追溯，上下文无法解释，冲突被静默覆盖，审计依赖手工日志。
- **新做法**：Context Graph + Decision Intelligence 层：Agent 的每个决策都是可查询的一等公民对象，带完整因果链和 W3C PROV-O 溯源。上下文不再是 embedding 向量，而是结构化知识图谱节点。冲突检测、实体解析、时间旅行内建。

## 生产力影响 (How)
为受监管行业（金融、医疗、法律、国防）打开了 Agent 落地之门。合规团队可以直接查询"为什么批准这笔贷款"并导出符合监管格式的审计报告。开发团队不需要重构——Semantica 作为底层基础设施插入现有 LLM + 向量数据库 + Agent 框架之下。

## 采用成本
pip install semantica，学习曲线中等（需理解 RDF/SPARQL/知识图谱概念），自托管，无 vendor lock-in

## 核心线索
- GitHub：https://github.com/semantica-agi/semantica
- 来源：https://github.com/semantica-agi/semantica
- 发布时间：2026-08-22
