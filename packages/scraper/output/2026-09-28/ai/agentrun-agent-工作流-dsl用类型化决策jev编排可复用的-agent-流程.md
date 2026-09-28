# AgentRun — Workflow DSL for Agents

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 提出"agent 工作流语言"+"类型化决策（Jev）"编排，工作流作为可审查文档 |
| 采用广度 | ☆☆/5 | 早期（0.1.0-beta.4），Parcha Labs 出品 |
| 时间新鲜 | ☆☆☆☆☆/5 | 新发布（beta） |
| 社区热度 | ☆☆/5 | Show HN 51 points（低于阈值，但结合 Jev 生态） |
| **总体判断** | ⚠️ | **观察中（新范式候选）** |

## 技术定义 (What)
面向已有 agent 的工作流 DSL：定义可重复步骤 + Jev 类型化决策 + 按需调用 agent。

## 行业痛点 (Why)
全 agent 贵且不可控、全函数无法处理判断，缺少中间编排层。

## 旧范式 vs 新范式
- **旧做法**：全 agent 或写死函数
- **新做法**：工作流文档 + Jev 判断阈值 + 按需 agent 调查

## 生产力影响 (How)
降低成本、提升可审查性，Jev 决策置信度阈值控制 agent 调用时机。

## 采用成本
低，Node + npm 即可。

## 风险/局限
早期 beta；代码节点有进程权限需沙箱；Jev 依赖 TypeSafe 平台。

## 核心线索
- GitHub：https://github.com/Parcha-ai/agentrun
- 发布：2026（beta 0.1.0）
- 当前状态：试验中