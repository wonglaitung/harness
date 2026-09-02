# Hermes Agent — 自成长Agent闭环学习循环

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ★★★★★/5 | 首个将"Agent自学→技能固化→自我改进"作为核心架构的Agent运行时。提出"closed learning loop"概念：自主技能创建→使用中自我改进→记忆持久化→跨会话用户建模 |
| 采用广度 | ★★★/5 | 兼容 agentskills.io 开放标准；支持 7 种终端后端 + 6 种消息平台；被 FrontierHarness Eval 评测收录 |
| 时间新鲜 | ★★★★★/5 | 2026年8月首发，GitHub trending 2026-09-02 |
| 社区热度 | ★★★★/5 | GitHub 529⭐/天（Python trending #1），FrontierHarness 收录为评测对象 |
| **总体判断** | ✅ | **新范式：Agent自主学习运行时** |

## 技术定义 (What)

Hermes Agent 是 Nous Research 构建的**自改进 AI Agent**。它不是传统的"输入→响应"Agent，而是内置了一个完整的**学习闭环**：完成复杂任务后自动创建可复用技能（skill），技能在使用中持续自我改进，通过周期性"记忆轻推"（memory nudges）将经验固化为持久知识，并通过 Honcho 辩证法用户建模跨会话构建用户画像。

## 行业痛点 (Why)

当前 Agent 的最大问题是**无记忆且不成长**：每次对话从零开始，重复劳动无法积累。传统 Agent 框架（LangChain、AutoGPT）关注的是工具调用和流程编排，但学不到"使用者的偏好"和"上次怎么做的"。

## 旧范式 vs 新范式

- **旧做法**：Agent = LLM + Tools + Prompt，每次对话独立，靠人工编写越来越长的 system prompt
- **新做法**：Agent = LLM + Tools + **Learning Loop**，自主从经验中提取技能并持续改进，跨会话记忆持久化

## 生产力影响 (How)

1. **技能自举**：完成一次复杂任务后，Agent 自动将工作流固化为可复用技能
2. **记忆持久化**：FTS5 全文搜索 + LLM 摘要实现跨会话回忆
3. **跨平台连续**：Telegram/Discord/Slack/WhatsApp/Signal/CLI 统一网关
4. **无厂商锁定**：支持任何模型（Nous Portal、OpenRouter、OpenAI、自托管）
5. **零成本闲置**：支持 Modal/Daytona 无服务器部署，闲置成本接近零

## 采用成本

- **时间**：`curl` 一行安装，5 分钟内可运行
- **金钱**：$5 VPS 或零成本 serverless
- **学习曲线**：低，自然语言交互

## 采用案例

- **FrontierHarness Eval**：Hermes v0.20.4 与其他 11 个编码 Agent 同台评测，50% 通过率
- **agentskills.io**：兼容开放技能标准，技能可跨 Agent 框架复用

## 风险/局限

- 学习循环的质量依赖底层模型能力
- 技能自改进可能固化错误模式
- 作为新产品，生态集成尚在早期

## 核心线索

- GitHub：https://github.com/NousResearch/hermes-agent
- 官网：https://hermes-agent.nousresearch.com/
- 创建者：Nous Research
- 当前状态：活跃开发中（2026年8月首发）