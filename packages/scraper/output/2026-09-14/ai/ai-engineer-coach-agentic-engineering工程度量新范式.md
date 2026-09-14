# AI Engineer Coach — Agentic Engineering 工程度量新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首次提出"Agentic Engineering"作为可度量的工程实践：Practice Scores、Anti-Patterns、Context Health、Skill Finder 等全新概念体系 |
| 采用广度 | ☆☆/5 | Microsoft 开源，早期社区采用中 |
| 时间新鲜 | ☆☆☆☆☆/5 | GitHub 2026-09 trending，极新 |
| 社区热度 | ☆☆☆/5 | GitHub trending 184 stars/day，Microsoft 品牌背书 |
| **总体判断** | ✅ | **新范式** — AI 辅助编程从"艺术"走向"工程" |

## 技术定义 (What)

AI Engineer Coach 是 AI 辅助编程的"工程度量仪表盘"。它读取本地 AI harness（Claude Code、Codex、Copilot）的 session logs，生成可操作的工程洞察。核心概念包括：

- **Practice Scores**（实践分数）：量化你的 AI 编程水平，含周趋势对比
- **45 条 Anti-Pattern 检测规则**：覆盖 prompt 质量、session 卫生、代码审查、工具精通度、上下文管理五大维度
- **Context Health（上下文健康度）**：Agentic Readiness 检查、instruction-file 审计、workspace 上下文图谱
- **Skill Finder**：从重复 prompt 模式中发现可复用的技能
- **Agentic SDLC**：追踪 AI 在完整软件开发生命周期中的使用分布

## 行业痛点 (Why)

AI 编程助手（Claude Code、Codex、Copilot）已被广泛使用，但**没有人知道怎么用得好**。开发者缺乏：
- 衡量自己 AI 编程水平的客观标准
- 识别低效使用模式的工具
- 团队级别的 AI 工程实践标准

这导致了"wild west"式的使用：有些人产出翻倍，有些人却越用越慢。

## 旧范式 vs 新范式

- **旧做法**：凭感觉使用 AI 编程助手，没有度量、没有反馈循环。只能靠"我觉得今天写得快/慢"来衡量
- **新做法**：Practice Scores + Anti-Pattern 检测 + Context Health 审计 → 可量化、可改进的 Agentic Engineering 循环

## 生产力影响 (How)

- 个人层面：从"先用再说"变为有反馈的刻意练习，45 条规则帮你发现自己在浪费 tokens、写低质量 prompt、上下文管理混乱等问题
- 团队层面：建立共享的 Agentic Engineering 标准，可以对比不同成员/项目的 AI 使用效率
- 管理者层面：看到 AI 在 SDLC 各阶段的使用分布，优化团队流程

## 采用成本

- 安装：从源码构建 VS Code 扩展（.vsix）或 GitHub Copilot Canvas 模式
- 零运行时成本：全本地分析，数据不离开机器
- 需要：Claude Code / Codex / Copilot 的 session logs

## 采用案例

- **Microsoft 内部**：由微软员工开源，已在内部使用
- 适用于任何使用 Claude Code、Codex、GitHub Copilot 的团队

## 风险/局限

- 尚未发布到 VS Code Marketplace，需手动构建
- 部分功能（Skill Finder、Learning Center）依赖 VS Code 内置 LM API
- 团队级别的比较和标准化尚在早期
- AI Anti-Pattern 的定义可能随模型演进快速过时

## 核心线索

- GitHub：https://github.com/microsoft/AI-Engineering-Coach
- 首发来源：GitHub Trending 2026-09-14
- 发布时间：2026-09（推测）
- 当前状态：活跃开发中
- License：MIT