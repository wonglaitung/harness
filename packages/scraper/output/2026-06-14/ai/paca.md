# Paca

## 技术定义 (What)
AI 原生的项目管理平台，让 AI Agent 作为正式成员加入 Scrum 团队，与人类平等协作。支持任务分配、BDD 场景编写、系统设计文档协作。

## 行业痛点 (Why)
现有项目管理工具（Jira/Trello/ClickUp）将 AI 视为外部聊天机器人，无法参与 Sprint 规划、看板更新、代码审查等核心流程。Agent 产出分散，无法与团队工作流集成。

## 旧范式 vs 新范式
- **旧做法**：人类在 Jira 上管理任务，Agent 在独立聊天窗口生成代码/文档。两套系统割裂，Agent 无法看到任务优先级、依赖关系、团队进度。
- **新做法**：Agent 作为 Scrum 团队成员出现在看板上，可被分配任务、更新状态、编写 BDD Gherkin 场景、参与系统设计。内置 MCP Server 连接任意 Agent，支持 Claude Code 技能直接操作。P-A-C-A 循环（Plan-Act-Check-Adapt）让团队与 Agent 共同迭代。

## 生产力影响 (How)
团队无需切换工具，Agent 直接在项目中协作。PO/BA 与 Agent 共同编写 BDD 场景，开发与 Agent 共同维护架构文档。所有活动可追溯、可回滚。

## 采用成本
Docker Compose 一键部署，自托管无数据外泄风险。Apache 2.0 开源免费，对比 Jira $8-20/人/月。需要 Docker 环境，学习成本中等。

## 核心线索
- GitHub：https://github.com/Paca-AI/paca
- 来源：https://github.com/Paca-AI/paca
- 发布时间：2026-06-14
