# agent-native

## 技术定义 (What)
Agent-Native 是首个 Agent-Native 应用框架，核心创新是"Agent 与 UI 平等协作"：一个 action 同时支持 UI 点击、Agent 调用、HTTP API、MCP 工具、A2A 通信、CLI 命令。Agent 能看到用户在看什么，能修改应用代码，能与另一个 Agent 协作，形成"自改进应用"。提供 6 个完整 SaaS 模板（Calendar/Content/Plans/Slides/Analytics/Clips），每个都是可克隆、可定制的开源应用。

## 行业痛点 (Why)
传统 SaaS 工具 AI 是附加的（"bolted on"），AI Agent 与 UI 分离，状态不同步。用户在 UI 点击，Agent 不知道；Agent 在聊天中操作，UI 不更新。开发者需要维护两套系统，AI 只能"聊"不能"做"。

## 旧范式 vs 新范式
- **旧做法**：旧做法：1) SaaS 工具 + 侧边栏 AI 聊天，两者独立；2) AI 只能通过 API 调用，无法直接操作 UI；3) 用户需要在 UI 和聊天之间切换，信息不同步；4) Agent 无法修改应用本身，只能给出建议
- **新做法**：新做法：1) 一个 action 定义，UI/Agent/API/MCP/A2A/CLI 共用；2) Agent 知道用户在看什么（上下文感知），能直接修改；3) 实时多人协作，人类和 Agent 平等编辑同一文档；4) Agent 能添加功能、修复 bug、优化 UI，应用自改进

## 生产力影响 (How)
开发者可快速构建 Agent-Native 应用，无需维护两套系统。用户享受"所见即所得"的 AI 协作体验，UI 和 Agent 完全同步。Agent 能真正"进入"应用而非仅聊天，开发者生产力提升 50%+（Builder.io 官方数据）。

## 采用成本
学习曲线：需要理解 action-first 架构，约 2-3 天上手。技术栈：TypeScript + Drizzle ORM + Nitro。成本：开源免费，需自建数据库和 hosting。模板开箱即用，可直接克隆定制。

## 核心线索
- GitHub：https://github.com/BuilderIO/agent-native
- 来源：https://github.com/trending/typescript
- 发布时间：2026-06-21
