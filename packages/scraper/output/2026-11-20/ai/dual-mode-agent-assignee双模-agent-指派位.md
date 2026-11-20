# Dual-Mode Agent Assignee（双模 Agent 指派位）

## 技术定义 (What)
让 Agent 成为项目管理系统里的一等"成员"：拥有角色、权限和 assignee 槽位，与人共用同一块看板；且每个 Agent 可二选一运行——内部 Agent 跑在你的服务器上（任意模型 + 你的 API key），外部 Agent 跑在成员自己的机器上、借用其已付费的 Claude Code / Codex / Copilot CLI / opencode 账号（通过 @itsaplan/runner）。

## 行业痛点 (Why)
Agent 一直被放在"工具面板"里，而不是"组织架构"里：任务派给 Agent 需要复制粘贴 prompt，产出无法进入 issue 流程，权限与审计完全缺失。同时企业面临两难——用服务器统一调用要额外买 API 额度，用员工现有 CLI 订阅又无法在系统内调度。

## 旧范式 vs 新范式
- **旧做法**：Agent = 侧边栏聊天框；任务交接靠人工搬运上下文；Agent 产出散落在对话记录里，不进 issue tracker；算力成本集中由平台方承担。
- **新做法**：Agent = 有 assignee 槽位的项目成员，可由 @提及、指派、或定时排程触发；工作流可让 issue 在 Agent → Agent 之间流转。关键创新是「双执行平面」：内部平面（服务端 + 任意模型）与外部平面（用户自己的 CLI 订阅 + 本机）并存，把"谁的账号付钱、谁的机器执行"变成可配置项，而非架构前提。

## 生产力影响 (How)
把 Agent 纳入既有研发管理流程（issue → 指派 → 评审 → 关闭），使 Agent 产出天然可审计、可回溯；外部 Agent 模式让企业无需先谈拢大额 API 合同即可试点，个人开发者可用已有订阅跑"自己的"Agent。

## 采用成本
低：自托管 Docker / Railway / Coolify 一键部署，自带 Linear / Trello / Plane 导入；支持 OIDC/SCIM、passkey。需要一台常驻服务器 + 数据库；外部 Agent 模式下每位成员的 CLI 需保持登录态。

## 核心线索
- GitHub：https://github.com/croffasia/itsaplan
- 来源：https://github.com/trending/typescript?since=daily
- 发布时间：2026-11-20
