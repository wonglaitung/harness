# Hindsight — "Agent Memory That Learns"

## 技术定义 (What)
Hindsight 是一个"会学习"而非"只记忆"的 Agent 记忆系统。它不再依赖 RAG 检索或知识图谱，而是通过 retain（存储）/ recall（召回）/ reflect（反思）三个操作，自动构建"心智模型"（mental models）与"知识页"（knowledge pages），让 Agent 随着使用时间增长而持续变聪明。

## 行业痛点 (Why)
现有 Agent 记忆系统（RAG、知识图谱、对话历史摘要）只能"回忆过去"，无法从经验中归纳出可复用的认知。Agent 往往是"金鱼记忆"，每次任务从零开始，无法累积能力。

## 旧范式 vs 新范式
- **旧做法**：RAG 向量检索 / 知识图谱 / 对话历史总结——都是被动"存档 + 检索"，Agent 无法主动学习、抽象、泛化。
- **新做法**：以"学习"为核心目标的记忆基础设施：分离记忆类型（episodic/semantic/procedural），通过 reflect 操作生成"心智模型"与"知识页"，把记忆从"检索库"升级为"可成长的认知引擎"。

## 生产力影响 (How)
两行代码的 LLM Wrapper 即可为现有 Agent 加上记忆；支持 25+ LLM Provider、Docker/Helm/嵌入式部署。在 LongMemEval 基准上刷新 SOTA，已被 Fortune 500 企业生产使用。

## 采用成本
低——pip/npm 安装客户端或 Docker 起服务即可，2 行代码集成；有托管云与免费额度。

## 核心线索
- GitHub：https://github.com/vectorize-io/hindsight
- 来源：https://github.com/vectorize-io/hindsight
- 发布时间：2026-09-25
