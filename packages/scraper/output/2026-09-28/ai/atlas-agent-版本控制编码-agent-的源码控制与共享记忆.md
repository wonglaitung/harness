# Atlas — Agent 版本控制

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆/5 | "Agent 版本控制"新类别，checkpoint 关联 commit→session |
| 采用广度 | ☆☆/5 | 早期，暂未见广泛集成 |
| 时间新鲜 | ☆☆☆☆☆/5 | 早期阶段 |
| 社区热度 | ☆☆☆☆/5 | GitHub trending 588 stars/day |
| **总体判断** | ✅ | **新范式（观察中）** |

## 技术定义 (What)
编码 Agent 的源码控制与跨 Agent 共享记忆系统。

## 行业痛点 (Why)
多 Agent 并行编码时变更来源混乱、无法回滚、上下文无法共享。

## 旧范式 vs 新范式
- **旧做法**：Agent 直接操作 git，面向人类的提交，状态割裂
- **新做法**：session/commit 关联 + 跨 Agent 共享记忆

## 风险/局限
- 早期项目，具体功能边界待确认
- 与现有 git 工作流的集成方式待验证

## 核心线索
- GitHub：https://github.com/trending/typescript
- 当前状态：试验中