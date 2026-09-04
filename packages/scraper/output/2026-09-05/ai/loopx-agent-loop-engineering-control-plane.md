# LoopX — Agent Loop Engineering Control Plane

## 技术定义 (What)
LoopX 是一个开源、provider-agnostic、local-first 的 Agent 控制平面（control plane），为长时间运行的 Agent 任务提供持久化状态管理。定位在"Loop Engineering"——一种新的 Agent 工程范式，将 Agent 从单次会话工具升级为跨天/跨 harness 的"数字员工"。

## 行业痛点 (Why)
Agent 可以完成单次任务，但多天工程/研究/实验目标无法持久化——目标变化、证据过时、Agent 交接、调度失控时缺乏治理层。Chat 记忆和定时器不足以管理 200+ 小时的长时间自主工作流。

## 旧范式 vs 新范式
- **旧做法**：Agent 任务限于单次会话（chat memory），长时间任务靠手动续跑；Chat 记忆丢失后 Agent 失去上下文；跨天/跨工具需要人工重新描述目标；多个 Agent 协作缺乏统一状态视图。
- **新做法**：Loop Engineering 范式：Agent 运行在"循环"中——每个循环包含目标(objective)、门控(gate)、待办(todo)、证据(evidence)、配额(quota)。人类在关键时刻做语义判断，Agent 在配额内执行有界切片。状态持久化在 LoopX state 中而非聊天记忆。跨 Codex/Claude Code/Cursor 等 harness 无缝续跑，不绑定任何提供商。

## 生产力影响 (How)
将 Agent 从"一次性工具"升级为"可持续交付的数字员工"。已展示 200+ 小时 OpenViking 贡献弧、Auto ML 实验线、7 个合并 PR 的真实案例。对长时间运行的工程/研究/实验工作流有直接生产力提升。

## 采用成本
pip install loopx，Python 3.11+，零外部依赖。学习曲线中等：需理解 goal/gate/todo/quota/evidence 等概念模型。目前与 Codex/Claude Code/Cursor 等 harness 适配。

## 核心线索
- GitHub：https://github.com/huangruiteng/loopx
- 来源：https://github.com/trending/python (2026-09-05 daily)
- 发布时间：2026-09-05
