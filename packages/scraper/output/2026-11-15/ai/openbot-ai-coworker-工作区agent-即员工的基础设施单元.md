# OpenBot — AI Coworker 工作区

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 明确提出「AI coworkers，每个 Bot 独占一台计算机」，并把治理语义（决定在前、记录在后、审批、审计）写进产品原语，而非事后加装 |
| 采用广度 | ☆☆/5 | 借 AG-UI 生态横向铺开：Claude Agent SDK、Microsoft Agent Framework / Agent Harness、Google ADK、AWS Strands（Bedrock AgentCore 直支持 AG-UI）、Oracle Agent Spec、LangChain、Mastra、Pydantic AI、Agno、CrewAI；工具层统一 MCP。但 OpenBot 本体尚新，独立引用待观察 |
| 时间新鲜 | ☆☆☆☆/5 | 当前 GitHub Trending TypeScript 日榜在列（Trendshift #3 of the day），属近期发布 |
| 社区热度 | ☆☆☆/5 | GitHub Trending 单日 +206 stars，Trendshift 日榜第 3；尚未积累 HN 大讨论 |
| **总体判断** | ✅ | **新范式（工作区层）** |

## 技术定义 (What)

OpenBot 是一个 MIT 许可、可白标的自托管「AI 同事工作区」：

- **三部分架构**：多端前端（Mac/Windows/Web/iOS/Android/Slack/Teams）→ OpenBot 后端 → 计算与工具（Kubernetes/兼容沙箱 + MCP）。
- **双层接入**：Agent 层用 **AG-UI**（有内置 Bot，也可把已有 Agent 从任意执行平台接进来）；工具层用 **MCP**。
- **治理内建**：公司登录、角色、工具权限、审批、审计统一作用于人与 Agent。
- **模型自由**：OpenAI、Claude、Gemini 或 OpenAI 兼容端点的开源模型，可自托管。

## 行业痛点 (Why)

企业卡在"Agent 进不了生产"，缺的不是能力而是**可治理性**：Agent 用哪台机器、能动哪些工具、能否代表公司下单/发信、谁批准、事后谁负责。这套语义过去由每个团队自拼，导致 PoC 无法收敛为平台。

## 旧范式 vs 新范式

- **旧做法**：Agent = 某 SaaS 里的侧边栏功能，模型/工具/UI/权限由厂商打包；换框架即重写；行动不可审计。
- **新做法**：Agent = 员工，工作区 = 部署单元。AG-UI 定义「Agent ↔ 前端」契约，MCP 定义「Agent ↔ 工具」契约，计算由 K8s/沙箱供给，策略统一施加；每个动作"决定在前、记录在后"。

## 生产力影响 (How)

- 企业第一次可以对 Agent **发工牌**：同一套权限/审批/审计横跨多 Agent、多端、多执行平台。
- 团队可以把 Agent 留在 Bedrock AgentCore、Claude Managed Agents、Google Agent Platform、Microsoft Foundry 上不动，只把工作区接过来 —— 避免 Agent 平台锁定。
- 前端与后端独立演进，UI 交互结果（interactive results）与计算机视图可按端自适应。

## 采用成本

- 个人/laptop：下载签名安装包即可（前端 + Docker 后端一体），零终端门槛。
- 团队：Helm 自托管到自家 K8s，需运维投入；商务版提供托管与定制。
- 开发：主要成本在 AG-UI 事件契约与 MCP 工具适配，官方有一线框架集成与 adapter。

## 采用案例

- **CopilotKit 自身生态**：作为 AG-UI 参考实现落地（CopilotKit 称其在多数 Fortune 500 企业生产使用）。
- **企业早期访问**：OpenBot for Business 提供 company sign-in、tool permissions、approvals、audit 四件套。

## 风险/局限

- **生态绑定反转风险**：高度依赖 AG-UI 与 CopilotKit 的演进节奏；AG-UI 若分裂，工作区价值打折。
- **自托管运维重量**：K8s + 沙箱 + 模型端点，中小企业落地成本不低。
- **新项目验证期**：本体独立引用与生产案例尚少，"AI coworker" 概念仍在形成期。
- **审计≠安全**：决定在前/记录在后提供可追溯性，但不等于沙箱逃逸、提示注入等风险被解决。

## 核心线索

- GitHub：https://github.com/CopilotKit/OpenBot
- 官网：https://open.bot
- 发现来源：GitHub Trending TypeScript（daily），206 stars today，Trendshift #3
- 发布时间：2026-11（近期）
- 当前状态：活跃（早期高速增长期）
