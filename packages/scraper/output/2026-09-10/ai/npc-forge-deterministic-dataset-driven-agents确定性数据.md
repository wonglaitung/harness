# NPC-Forge — Deterministic Dataset-Driven Agents（确定性数据集驱动 Agent）

## 技术定义 (What)
NPC-Forge 是一个无 LLM 的确定性对话 Agent 框架。它用精心策划的数据集（NDF 格式）完全取代概率模型，在 CPU 上实现毫秒级响应、零幻觉、零对齐过滤。通过 OpenAI 兼容 API 即可接入任何 LLM harness，让"小任务"不需惊动大模型。核心理念：许多问题不需要 ML——用确定性设计 + 社区策划数据集来构建 Agent。

## 行业痛点 (Why)
(1) LLM 对于简单任务过度杀鸡用牛刀——NVIDIA 研究发现 40-70% 的 Agent 调用可以用小/专用模型替代；(2) LLM 的幻觉和不可预测性在确定性需求场景下是致命缺陷；(3) GPU/API 成本让高频简单任务不可持续；(4) 对齐过滤器可能拒绝合法请求。

## 旧范式 vs 新范式
- **旧做法**：所有对话 Agent 都依赖 LLM——即使是简单任务（如"把自然语言转成 shell 命令"）也要跑一个大模型，消耗 GPU/API 成本、有幻觉风险、需要对齐过滤、有延迟。
- **新做法**：确定性数据集驱动 Agent：开发者编辑人类可读的 NDF 数据集文件 → 执行 `npc-forge reboot` → Agent 即时更新行为。零训练、零 GPU、零幻觉。OpenAI 兼容 API 使这些确定性 Agent 可无缝嵌入现有 LLM 工作流中，作为第一道过滤层或纯确定性任务执行器。

## 生产力影响 (How)
为 Agent 架构引入"确定性层"概念：将高频、简单、需要 100% 可靠的任务下沉到 NPC-Forge 层，只在需要推理能力时才调用 LLM。这可以降低 Agent 系统 40-70% 的 LLM 调用量（参考 NVIDIA 研究），同时提升可靠性和响应速度。TERNMy 已展示了将自然语言→shell 命令的转化做到毫秒级和 100% 确定性的实际效果。

## 采用成本
极低成本：Linux/WSL 环境，5MB 级框架，无需 GPU，无需训练，数据集即配置。AGPL-3.0 开源协议。学习曲线平缓：只需编辑 NDF 格式数据集。

## 核心线索
- GitHub：https://github.com/gioblu/NPC-Forge
- 来源：https://news.ycombinator.com/item?id=Show+HN%3A+TERMy
- 发布时间：2026-09-10
