# 12-Factor Agents

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次系统化定义"LLM 驱动软件"的12条工程原则，类比 12-Factor Apps 对 Web 应用的定义 |
| 采用广度 | ☆☆☆/5 | AI Engineer World's Fair 主题演讲，GitHub 204 stars/day，社区讨论活跃 |
| 时间新鲜 | ☆☆☆☆/5 | 2025年发布，持续更新中 |
| 社区热度 | ☆☆☆/5 | AI Engineer World's Fair 17分钟主题演讲，YouTube 深度讨论 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)
一套用于构建可靠 LLM 驱动软件的12条工程原则。核心洞察：生产级 Agent 不是"提示词+工具循环"，而是主要由确定性代码构成、LLM 在关键决策点介入的软件系统。

## 行业痛点 (Why)
当前 Agent 框架（LangChain/CrewAI/LangGraph 等）几乎没有被用于面向客户的生产环境。大多数声称的"AI Agent"本质上并不 agentic，而是确定性代码 + LLM 步骤的混合体。行业缺乏构建可靠 LLM 软件的工程共识。

## 旧范式 vs 新范式
- **旧做法**：给 LLM 一个提示词 + 一袋工具，循环直到达成目标（"prompt + tools + loop"模式）
- **新做法**：将 Agent 视为状态化 reducer，拥有自己的控制流、上下文窗口、错误压缩，LLM 仅作为自然语言到工具调用的转换层

## 生产力影响 (How)
为 Agent 开发者提供可参照的工程标准，避免重复踩坑。Factor 3（Own your context window）单独就值回票价——上下文工程正在取代提示词工程成为核心技能。Factor 12（Make your agent a stateless reducer）为 Agent 的可扩展性提供了架构指导。

## 采用成本
- 时间：阅读完整文档约 2-3 小时，实践应用需 1-2 周
- 金钱：免费（Apache 2.0 开源）
- 学习曲线：需要理解 DAG 编排、状态管理、reducer 模式等概念

## 采用案例
- humanlayer.dev：基于 12-Factor 原则构建的生产级 Agent 平台
- 社区 `npx/uvx create-12-factor-agent` 脚手架正在开发中（GitHub Discussions #61）

## 风险/局限
- 仍是原则性指导，非可直接引用的代码框架
- 部分原则（如 Factor 12 stateless reducer）在长任务场景下实现复杂
- 缺乏大规模生产验证的公开案例

## 核心线索
- GitHub：https://github.com/humanlayer/12-factor-agents
- 首发来源：AI Engineer World's Fair 主题演讲
- 发布时间：2025年
- 当前状态：活跃开发中