# Hindsight

## 技术定义 (What)
Agent 记忆系统，专注于"学习"而非"记忆"。使用仿生数据结构组织记忆：World Facts（世界知识）、Experiences（经历）、Mental Models（心智模型）。在 LongMemEval 基准测试中达到 SOTA 性能。

## 行业痛点 (Why)
现有记忆系统只记录对话历史或简单的向量检索。Agent 无法从经验中学习，无法形成因果关系理解，无法基于过去改进未来行为。

## 旧范式 vs 新范式
- **旧做法**：使用 RAG（向量搜索）或知识图谱存储记忆。Agent 只能"回忆"相似内容，无法"学习"和"推理"。
- **新做法**：Hindsight 区分三种记忆类型：World（客观事实）、Experiences（主观经历）、Mental Models（习得理解）。通过 `reflect` 操作从原始记忆生成洞察。支持时间序列、实体关系、多模态。已在 Fortune 500 企业生产环境使用。

## 生产力影响 (How)
让 Agent 从"检索工具"进化为"学习系统"。Agent 可以反思过去行为、形成心智模型、预测未来结果。适用于 AI 员工、长期助手、需要持续学习的场景。

## 采用成本
需要 Python 3.10+，配置 LLM API 密钥。提供 Docker 部署（开箱即用）、嵌入式 Python（无需服务器）、云服务。学习曲线：2-3 小时掌握三种记忆类型和三个操作。

## 核心线索
- GitHub：https://github.com/vectorize-io/hindsight
- 来源：https://github.com/trending/python
- 发布时间：2026-06-22
