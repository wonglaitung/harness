# Agent Skills Standard

## 技术定义 (What)
一个开放的 Agent 技能标准（agentskills.io），定义了可移植的指令集，教会 AI Agent 如何最优地使用特定软件、框架或工具。技能以文件夹形式组织，包含 SKILL.md 文件（YAML frontmatter + Markdown 指令），支持跨平台分发和安装。

## 行业痛点 (Why)
AI Agent 缺乏结构化的领域知识，无法像资深从业者一样执行专业任务（如网络安全分析、GPU 优化）。现有方案要么是通用 LLM（缺乏深度），要么是硬编码脚本（缺乏灵活性）。

## 旧范式 vs 新范式
- **旧做法**：为每个任务手写 Prompt 或开发专用工具，知识无法复用，Agent 无法跨任务迁移能力
- **新做法**：技能即代码：将领域知识结构化为可安装、可复用、可组合的技能包，Agent 动态加载并按需执行

## 生产力影响 (How)
大幅降低 Agent 专业能力门槛。开发者可通过 `npx skills add` 一键安装 817 个网络安全技能或 NVIDIA 全栈 GPU 技能，Agent 立即获得专家级执行能力。

## 采用成本
极低：遵循 agentskills.io 标准，仅需创建 SKILL.md 文件。已有 NVIDIA、Anthropic 官方技能库，支持 Claude Code、Cursor、Codex 等 26+ 平台。

## 核心线索
- GitHub：https://github.com/anthropics/skills
- 来源：https://github.com/trending/python
- 发布时间：2026-06-23
