
# 12-Factor Agents

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次系统化提出 LLM 应用的工程原则框架，类比 12-Factor Apps 对 Web 应用的范式定义 |
| 采用广度 | ☆☆☆/5 | AI Engineer World's Fair 主题演讲，GitHub 高星，多家 YC 创始人参考 |
| 时间新鲜 | ☆☆☆☆/5 | 2025 年中首次发布，2026 年持续迭代，新增 create-12-factor-agent 脚手架 |
| 社区热度 | ☆☆☆☆/5 | GitHub Trending (204 stars/day)，AI Engineer 大会演讲 17 分钟，YouTube 深度视频 |
| **总体判断** | ✅ | **新范式——Agent 工程化的首个系统性原则框架** |

## 技术定义 (What)

12-Factor Agents 是一套面向 LLM 驱动软件的工程原则，灵感来自 12-Factor Apps。它提出：好的 Agent 不是"给 LLM 一个 prompt + 一堆工具然后循环"，而是**主要由确定性代码构成、在关键节点嵌入 LLM 能力的软件系统**。核心主张是 Agent 应该是**无状态归约器（stateless reducer）**——接收输入、产生输出、状态外置，而非有状态的自主循环体。

12 条原则：
1. 自然语言 → 工具调用（Natural Language to Tool Calls）
2. 拥有你的提示词（Own Your Prompts）
3. 拥有你的上下文窗口（Own Your Context Window）——即 Context Engineering
4. 工具即结构化输出（Tools Are Just Structured Outputs）
5. 统一执行状态和业务状态（Unify Execution State and Business State）
6. 启动/暂停/恢复的简单 API（Launch/Pause/Resume）
7. 通过工具调用联系人类（Contact Humans with Tool Calls）
8. 拥有你的控制流（Own Your Control Flow）
9. 压缩错误到上下文窗口（Compact Errors into Context Window）
10. 小而专注的 Agent（Small, Focused Agents）
11. 从任何地方触发，在用户所在处响应（Trigger from Anywhere）
12. 让 Agent 成为无状态归约器（Make Your Agent a Stateless Reducer）

## 行业痛点 (Why)

当前 Agent 开发存在三大痛点：
1. **框架陷阱**：大多数 Agent 框架（LangChain/LangGraph/CrewAI 等）在生产环境中表现不佳，YC 创始人们都在自己造轮子
2. **伪 Agent 泛滥**：市场上标榜"AI Agent"的产品大多只是确定性代码 + 少量 LLM 调用，但开发者却用沉重的框架去构建
3. **缺乏工程共识**：没有公认的"Agent 该怎么构建"的方法论，导致每个团队都在重复踩坑

## 旧范式 vs 新范式

- **旧做法**：给 LLM 一个 prompt + 一袋工具，让它在循环中自主决策直到达成目标（ReAct 模式）。Agent 框架负责编排，开发者写 prompt 和工具定义
- **新做法**：Agent 是确定性软件，LLM 只在需要的节点介入。开发者拥有控制流、提示词、上下文窗口，Agent 是无状态的归约器。状态外置，人类通过工具调用介入，错误被压缩回上下文而非被忽略

## 生产力影响 (How)

1. **降低生产部署风险**：明确"own your control flow"让 Agent 行为可预测、可调试
2. **减少框架依赖**：不依赖黑盒框架，用普通代码构建 Agent，降低维护成本
3. **提高可观测性**：统一执行状态和业务状态，让调试和监控变得简单
4. **加速开发**：12 条原则提供清晰的架构检查清单，减少试错时间
5. **Context Engineering 成为一级公民**：Factor 3 首次将上下文工程提升到与 prompt 工程同等重要的位置

## 采用成本

- **时间成本**：阅读 12 篇 Factor 文章约 2-3 小时
- **金钱成本**：完全免费（开源 Apache 2.0）
- **学习曲线**：低——原则性指导而非代码框架，不需要学习新 API
- **实施成本**：中——需要重新审视现有 Agent 架构，但可以渐进式采用

## 采用案例

- **Humanlayer**：项目作者自己的产品，基于 12-Factor 原则构建的人类介入层
- **AI Engineer World's Fair**：2025 年大会主题演讲，影响数千名 AI 工程师
- **create-12-factor-agent**：社区正在开发脚手架工具，将原则转化为代码模板
- **多家 YC 创业公司**：据作者称，生产环境中面向客户的 Agent 大多采用了类似原则

## 风险/局限

- **原则而非实现**：这是指导性框架，不是可运行的代码库，需要开发者自行落地
- **验证尚不充分**：虽然逻辑自洽，但大规模生产验证案例仍有限
- **可能与框架生态冲突**：现有框架（LangGraph 等）的设计理念与 12-Factor 有根本分歧
- **持续演进中**：部分 Factor 仍在讨论和迭代，尚未完全稳定

## 核心线索

- GitHub：https://github.com/humanlayer/12-factor-agents
- 首发来源：AI Engineer World's Fair 2025 主题演讲
- 发布时间：2025 年中
- 当前状态：活跃（2026 年 6 月仍在 GitHub Trending，社区讨论活跃）
