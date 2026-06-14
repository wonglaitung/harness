# Agent Glossary

## 技术定义 (What)
Hugging Face 发布的 Agent 核心术语体系，明确定义 Model、Scaffold、Harness、Agent、Tool Use、Skills 等概念的边界和关系，解决 ICLR 2026 以来社区术语混用问题。

## 行业痛点 (Why)
Agent 领域术语模糊，"harness" 和 "scaffold" 在不同框架中含义相反。ICLR 2026 后从业者反馈"听了很多解释但无法收敛到单一答案"，阻碍技术交流和框架互操作。

## 旧范式 vs 新范式
- **旧做法**：各框架自行定义术语，Claude Code 称"整个都是 harness"，其他框架区分 scaffold/harness。无统一标准，学术论文和工程实践术语不互通。
- **新做法**：定义清晰的层次结构：Model（LLM）→ Scaffold（行为定义层：系统提示、工具描述、上下文管理）→ Harness（执行层：调用模型、处理工具调用、决定何时停止）→ Agent（Model + Harness）。补充 Policy、Tool Use、Skills、Sub-agents 等概念，覆盖训练和推理两阶段。

## 生产力影响 (How)
开发者可精确讨论"我要改 scaffold 还是 harness"，避免歧义。框架作者有术语参考，降低用户学习成本。学术论文与工程实践术语对齐。

## 采用成本
概念性知识，无需安装。阅读博客即可理解，适合所有 Agent 从业者。可作为团队内部术语标准。

## 核心线索
- GitHub：https://huggingface.co/blog/agent-glossary
- 来源：https://huggingface.co/blog/agent-glossary
- 发布时间：2026-06-14
