# DESIGN.md — AI Agent 的视觉身份规范

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首次为 AI Coding Agent 定义结构化视觉身份文件格式，YAML tokens + Markdown prose 双层结构 |
| 采用广度 | ☆☆☆☆/5 | Google 官方出品，727 stars/day，已发布 npm CLI 工具，支持 Tailwind/DTCG 导出 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2025年6月首次公开发布，极新 |
| 社区热度 | ☆☆☆☆/5 | GitHub TS Trending #2（727 stars/day），社区高度关注 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)
DESIGN.md 是一种文件格式规范，用于向 AI Coding Agent 描述视觉身份系统。它将机器可读的设计 token（YAML front matter）与人类可读的设计理念（Markdown 正文）结合，让 Agent 在生成 UI 时拥有持久、结构化的设计理解。

## 行业痛点 (Why)
AI Coding Agent（Claude Code、Codex、Cursor 等）生成 UI 时缺乏一致的设计约束。每次生成都是"从零开始"，无法保持品牌一致性。现有的 design token 系统面向人类开发者，Agent 无法有效消费。

## 旧范式 vs 新范式
- **旧做法**：在 prompt 中用自然语言描述设计风格，或依赖 Agent 从现有代码推断风格，结果不一致且不可重复
- **新做法**：在项目根目录放置 DESIGN.md，Agent 自动读取结构化 token（颜色、字体、间距、圆角、组件），生成符合品牌规范的 UI

## 生产力影响 (How)
开发者无需在每次对话中重复描述设计规范。Agent 一次读取 DESIGN.md 即可持续产出风格一致的 UI。CLI 提供 lint（验证结构+WCAG对比度）、diff（版本间 token 变更检测）、export（导出 Tailwind/DTCG 格式）三大工具。

## 采用成本
- 学习成本：低。YAML + Markdown 格式，前端开发者零门槛
- 集成成本：极低。`npx @google/design.md lint DESIGN.md` 即可验证
- 迁移成本：中等。需从现有设计系统提取 token 写入 DESIGN.md

## 采用案例
- Google 内部项目已使用
- 可与 Claude Code、Codex、Cursor 等 Agent 无缝配合
- 导出 Tailwind v3/v4 主题配置，直接用于前端项目

## 风险/局限
- 目前版本为 alpha，规范可能变更
- 仅覆盖视觉身份，不包含交互逻辑/动画规范
- 依赖 Agent 主动读取文件，需 Agent 生态配合

## 核心线索
- GitHub：https://github.com/google-labs-code/design.md
- npm：@google/design.md
- 首发来源：GitHub Trending
- 发布时间：2025年6月
- 当前状态：活跃（alpha）