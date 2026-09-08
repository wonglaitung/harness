# AI-DLC Workflows 2.0 — Harness-Neutral Agent Methodology 新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首次提出「harness-neutral core + thin surface」架构，方法论与实现完全解耦 |
| 采用广度 | ☆☆☆/5 | 支持 7 个主流 Agent 平台；AWS 官方背书；GitHub trending |
| 时间新鲜 | ☆☆☆☆/5 | v2.0 GA 宣布于近期，v2.7.1 活跃开发中 |
| 社区热度 | ☆☆☆/5 | GitHub trending TypeScript；AWS Labs 维护 |
| **总体判断** | ✅ | **新范式：Harness-Neutral Agent Methodology** |

## 技术定义 (What)
AI-DLC 将 AI 驱动的软件开发定义为 5 Phase/33 Stage 的严格门控流程，由 14 个专业 Agent 协作执行。核心创新在于架构：方法论逻辑存在于 harness-neutral 的 `core/` 中，各平台分发由同一源自动生成。

## 行业痛点 (Why)
Agent 碎片化：每个平台（Claude Code、Codex、Cursor 等）有自己的 skills/hooks/agents 语法。同一开发流程在不同平台无法复用，团队被锁定在单一平台。

## 旧范式 vs 新范式
- **旧做法**：为每个 Agent 平台单独编写和维护 skills/hooks/agents
- **新做法**：方法论写一次（core/），自动生成 7+ 平台的原生分发，所有平台从同一源获得相同待遇

## 生产力影响 (How)
- 14 个专业 Agent（11 领域专家 + 2 审查 + 1 自适应编排器）分工协作
- 33 阶段覆盖从初始化到运营的完整生命周期
- Learning Loop：人类纠正自动转化为持久行为规则
- 91 事件审计追踪满足企业合规需求
- 支持 11 种自适应 Scope（enterprise → express）

## 采用成本
- 安装 bun + 复制 dist/ 文件到项目
- 学习曲线：理解 Phase/Stage 框架需半天
- 推荐模型：Claude Opus 4.8

## 采用案例
- AWS 内部使用
- 支持 Claude Code、Kiro IDE/CLI、Codex CLI、Cursor、opencode、GitHub Copilot

## 风险/局限
- 较弱模型可能跳过可选步骤或仓促通过审批门
- 仍在积极开发中（pre-1.0 语义版本）
- 需要团队适应门控式开发流程

## 核心线索
- GitHub：https://github.com/awslabs/aidlc-workflows
- 首发来源：AWS DevOps Blog + GitHub
- 当前状态：活跃开发（v2.7.1）
- 关键文件：v2.0 白皮书 (assets/AI-DLC-Workflows-2.0-Specification.pdf)