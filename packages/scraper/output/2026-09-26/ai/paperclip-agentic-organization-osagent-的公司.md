# Paperclip — Agentic Organization OS（Agent 的公司）

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 将多 Agent 编排提升为"公司治理"，引入 org chart / budget / governance / goal alignment / heartbeats |
| 采用广度 | ☆☆☆/5 | 早期项目，采用尚在起步 |
| 时间新鲜 | ☆☆☆☆☆/5 | 新发布项目 |
| 社区热度 | ☆☆☆/5 | 早期传播阶段 |
| **总体判断** | ⚠️ | **观察中（概念创新强，采用广度 + 社区共鸣待验证）** |

## 技术定义 (What)
把多 Agent 编排提升为"公司治理"范式：组织架构图（org chart）、预算管理、治理规则、目标对齐、心跳调度（heartbeats）四大支柱，让 Agent 群像公司一样被管理。

## 行业痛点 (Why)
现有多 Agent 框架（AutoGen、LangGraph）本质是"任务图/DAG 编排"，缺乏组织治理概念——无预算控制、目标对齐、监督追责。Agent 数量增长后，编排/成本/目标失控成为核心痛点。

## 旧范式 vs 新范式
- **旧做法**：任务图/DAG 编排（AutoGen、LangGraph）——节点和边描述工作流，无治理/预算/对齐
- **新做法**：公司治理（org chart + budget + governance + goal alignment + heartbeats）——Agent 群像组织一样被管理协调

## 生产力影响 (How)
将 Agent 编排从"工程任务图"提升为"组织管理"，引入预算控制和目标对齐，大规模 Agent 部署可控可治理。

## 采用成本
较高：需理解组织治理抽象，重构现有多 Agent 编排逻辑，学习曲线较陡。

## 采用案例
- 早期阶段，暂无大型生产案例

## 风险/局限
- 采用广度不足，生态待成熟
- 治理抽象对小型任务可能过度设计

## 核心线索
- GitHub：https://github.com/paperclip-agent/paperclip
- 当前状态：试验中