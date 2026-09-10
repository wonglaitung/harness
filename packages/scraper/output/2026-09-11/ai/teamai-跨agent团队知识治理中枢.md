# TeamAI — 跨Agent团队知识治理中枢

## 技术定义 (What)
TeamAI 是一个跨 Agent 的团队知识治理 CLI 工具，将团队的 skills、rules、MCP 配置、知识库以 Git repo 形式统一管理，自动同步到 Claude Code、Codex、Cursor、CodeBuddy 等 11+ 种 AI 编码 Agent 中。核心理念：「One Team. One Harness. Every Agent.」

## 行业痛点 (Why)
团队中每个开发者使用不同的 AI 编码工具（Claude Code、Cursor、Codex 等），导致团队知识（编码规范、项目上下文、MCP 工具配置）分散不统一。新成员入职需要分别配置多个工具，规范变更无法全局同步。

## 旧范式 vs 新范式
- **旧做法**：每个开发者独立配置自己的 AI 编码工具，团队规范靠文档/wiki 手动传播，各 Agent 之间的 skills 和 rules 互不兼容，知识无法共享。
- **新做法**：团队管理员在一个 Git repo 中定义 skills/rules/MCP/knowledge，所有成员的 AI Agent 通过 `teamai pull` 自动同步最新配置。支持角色映射（Role→Namespace）、标签订阅（Tags）、多源聚合（Sources），实现「Harness as Code」的团队级 Agent 治理。

## 生产力影响 (How)
消除团队 AI 编码工具的配置碎片化，新成员一行命令接入团队全部 AI 知识资产。同时支持 Team Context（代码库图谱、learnings）和 Team Improvement（sessions、dashboard），形成团队 AI 能力的持续积累和优化的闭环。

## 采用成本
极低：npm install -g teamai-cli，需要一个 Git repo。学习曲线平缓。目前覆盖 11+ Agent，腾讯开源 MIT 协议。

## 核心线索
- GitHub：https://github.com/Tencent/teamai-cli
- 来源：https://github.com/Tencent/teamai-cli
- 发布时间：2026-09-11
