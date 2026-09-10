# TeamAI — 跨Agent团队知识治理新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆/5 | "Team Harness"概念有一定新颖性，摩擦驱动学习共享机制独特。但本质上是配置管理的 GitOps 思路 |
| 采用广度 | ☆☆/5 | 837 stars，腾讯出品，但尚未见第三方大规模采用 |
| 时间新鲜 | ☆☆☆☆☆/5 | 当日 GitHub trending 837 stars，极新 |
| 社区热度 | ☆☆☆/5 | 837 stars，10+ Agent 兼容矩阵 |
| **总体判断** | ⚠️ | **观察中** — 团队 AI 治理工具有实际价值，但概念创新度未达范式级 |

## 技术定义 (What)
腾讯开源的团队 AI 治理 CLI：通过 Git 仓库统一分发 skills/rules/MCP/知识库到 10+ 个 AI 编码代理。独创三层架构：Team Execution → Team Context → Team Improvement。

## 行业痛点 (Why)
团队使用多种 AI 编码工具导致能力碎片化——配置不统一、最佳实践无法传播、踩坑经验无法系统化利用。

## 旧范式 vs 新范式
- **旧做法**：各自配置 AI 工具，经验靠口头传递
- **新做法**：Git 仓库作为 AI 能力单一真相源，摩擦信号驱动自动知识沉淀

## 生产力影响 (How)
- 新成员即装即用全团队 AI 能力
- 摩擦驱动学习共享让踩坑经验自动沉淀到 AI 上下文
- 消除多工具碎片化配置

## 采用成本
npm 全局安装，需要 Git 仓库。管理员配置中等，成员使用极低。

## 采用案例
- 兼容 Claude Code / Codex / Cursor / CodeBuddy / OpenCode / Hermes 等 10+ Agent
- 腾讯内部使用

## 风险/局限
- 依赖 Git 工作流，需团队有 code review 习惯
- 摩擦信号检测可能不准确（误报/漏报）
- Team Context / Team Improvement 仍在 beta

## 核心线索
- GitHub：https://github.com/Tencent/teamai-cli
- 首发来源：GitHub trending TypeScript (2026-09-10)
- 发布时间：~2026-09-09
- 当前状态：活跃，腾讯官方维护