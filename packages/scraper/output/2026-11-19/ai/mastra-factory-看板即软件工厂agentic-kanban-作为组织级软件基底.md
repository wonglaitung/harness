# Mastra Factory — 看板即软件工厂：Agentic Kanban 作为组织级软件基底

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 明确定义 "software factory" 为「可配置 agentic 看板 + Slack 可 @ 的 durable 会话」，并给出工厂与目标仓库分离的架构约束；配套 durable agents / conversational memory / 带引用 wiki / PR 评论信号四件套 |
| 采用广度 | ☆☆☆/5 | Mastra 本体已达 ~4M 周下载；Factory 已用于维护 Mastra 自身（一周 238 agent PR + 630 人类 PR），并已出现独立同类实现（redbeardlab factory + dotFactory DSL） |
| 时间新鲜 | ☆☆☆☆/5 | 2026-11-19 Show HN 首发（Factory 本体新发布）；母项目 Mastra 约两年前发布，Factory 为新增层 |
| 社区热度 | ☆☆/5 | Show HN 83 分、31 评论（低于 100 门槛，但评论质量高且含独立竞品自荐） |
| **总体判断** | ⚠️ | **观察中偏新范式**——概念与自证案例扎实，但社区热度未达 HN≥100 / GitHub≥1k 门槛 |

## 技术定义 (What)
Mastra Factory 把软件开发流程本身重构为一个「可配置的 agentic 看板」：GitHub/Linear/Jira 上的 issue 自动进入 Intake 列，点击 Investigate 后启动一个 durable agent 会话，agent 自行产出 plan → 实现 → 提交 PR → 评审。关键设计是**工厂与被改仓库分离**（Factory 作为独立服务运行，不寄生在被改代码库中），以及**入口从 Web UI 漂移到 Slack**——工程师在 Slack 里 @ 一下看板就并行拉起 20 个会话。底层复用 Mastra 的 durable agents、conversational memory、带引用的 markdown wiki、PR 评论信号订阅，以及可插拔 cloud sandbox + coding harness（在支持 Claude Code、Codex 等）。

## 行业痛点 (Why)
单个 coding agent 提升的是「一个任务」的吞吐，但组织级瓶颈在流程编排：issue 分诊、排期、谁在做什么、评审交接全靠人肉。团队规模一大，agent 越多反而越混乱，因为没有任何东西持有「工作项 → 会话 → PR」的状态机。同时多 agent 并行时，人类无法同时盯住 20 个终端。

## 旧范式 vs 新范式
- **旧做法**：工程师开 N 个终端窗口，每个窗口跑一个 Claude Code / Codex 会话，靠人脑记住哪个在做什么；issue 到 PR 的流转靠项目管理工具 + 人工搬运；并行度受限于人能盯住几个终端。
- **新做法**：工作项本身是调度单元。看板列（triage/plan/build/review/shipped）即状态机，每个 issue 进入列就自动绑定 durable 长时会话，会话可由 Slack 消息驱动与交接。人类的工作从「操作 agent」变成「审核产出」——Mastra 团队实测上周 Factory 开并合 238 个 PR，人类另合 630 个。

## 生产力影响 (How)
- **并行度解耦**：从「人盯终端」变为「看板排队」，资深工程师可一次甩出 20 个 issue 让 agent 群处理
- **角色边界拓展**：Slack 作为主入口，使非工程师也能触发、转发 agent 会话
- **组织信号**：团队已关闭仓库外部 PR 通道，改为要求提交详细复现 issue——当 agent 产 PR 成本趋零，开源协作的「边际价值 PR」会洪水化，维护者只能转向 issue-only 模式

## 采用成本
- 中低。`npm create factory` 一键脚手架
- 依赖：PostgreSQL（pgvector）、模型 provider key（支持订阅）、GitHub App 授权
- 可完全自托管（`--no-platform`）或用 Mastra platform 托管 sandbox
- 真实成本在设计 intake 路由与看板列，而非技术集成；已有 Mastra 栈的团队近乎零迁移

## 采用案例
- **Mastra 自身**：一周 238 个 agent PR + 630 个人类 PR；已从 Web UI 主驱动转为 Slack 主驱动；使用 bug/vuln 扫描器作为前置信号
- **redbeardlab factory**：独立实现，连带自研 dotFactory DSL（触发器支持 webhook/PR/issue/cron，含 manual gate 与容器步骤），证明该形态可被独立复现

## 风险/局限
- 社区热度未达严格门槛（HN 83 分），能否扩散待观察
- 「关闭外部贡献」这一路径本身是社区治理风险，可能反噬开源生态信任
- durable agent 长时间运行 + 云端 sandbox = 成本与权限半径同时放大，需要组织级审计策略
- Factory 是 Mastra 之上的应用层示范，与其他 agent 框架（非 Mastra）耦合度低但迁移成本高

## 核心线索
- GitHub: https://github.com/mastra-ai/template-factory
- 文档站: https://factory.mastra.ai/
- Show HN: https://news.ycombinator.com/item?id=50548660 （83 points, 31 comments）
- 发布时间: 2026-11-19
- License: Apache-2.0
- 当前状态: 活跃（团队自用中）