# DESIGN.md

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次定义"设计系统即代码"的机器可读规范，YAML front matter + Markdown prose 双层结构，为 AI 编码代理提供持久化设计理解 |
| 采用广度 | ☆☆☆/5 | Google Labs 出品，已发布 npm CLI 工具，与 HyperFrames 等项目形成生态联动 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年6月首次公开发布，极早期 |
| 社区热度 | ☆☆☆/5 | GitHub TS Trending 首位，尚无 HN 大规模讨论 |
| **总体判断** | ✅ | **新范式** — 满足概念创新 + 时间新鲜 + 早期采用迹象 |

## 技术定义 (What)
DESIGN.md 是一种格式规范，将视觉身份描述为编码代理可理解的持久化文件。它结合 YAML front matter（机器可读的设计 token：颜色、字体、圆角、间距、组件）与 Markdown prose（人类可读的设计理念和上下文），让 AI 代理在生成 UI 时拥有结构化的设计系统理解，而非依赖零散的 prompt 指令。

## 行业痛点 (Why)
AI 编码代理（Claude Code、Codex、Cursor 等）在生成 UI 时缺乏持久化的设计系统理解。每次生成都是"从零开始"，导致风格不一致、token 引用混乱、无 WCAG 可访问性验证。设计系统散落在 Figma、CSS 变量、组件库中，代理无法统一消费。

## 旧范式 vs 新范式
- **旧做法**：在 prompt 中描述设计偏好，或依赖 CSS 变量/设计系统文档，代理每次会话丢失设计上下文
- **新做法**：DESIGN.md 作为项目根目录的单一真相源，代理自动读取 token 值和设计理念，生成一致 UI；CLI 提供 lint（结构校验 + WCAG 对比度检查）和 diff（token 级变更检测）

## 生产力影响 (How)
开发者不再需要在每次 prompt 中重复描述设计偏好。代理读取 DESIGN.md 后自动应用正确的颜色、字体、间距和组件规范。lint 工具自动检测 WCAG 对比度问题和 token 引用错误，diff 工具追踪设计系统演进。预计减少 50%+ 的 UI 生成迭代轮次。

## 采用成本
- 时间：30 分钟编写首个 DESIGN.md
- 金钱：免费（开源 MIT）
- 学习曲线：低 — YAML + Markdown，前端开发者零门槛

## 采用案例
- **HyperFrames**：HeyGen 的视频生成框架已集成 DESIGN.md 作为视频设计 token 源
- **Agent-Native**：BuilderIO 的 agent-native 框架在 design 模板中引用 DESIGN.md
- 任何使用 Claude Code / Codex / Cursor 的项目均可通过 `npx @google/design.md lint` 接入

## 风险/局限
- 规范仍处于 alpha 阶段，token schema 可能变更
- 仅覆盖视觉设计 token，不涉及交互逻辑和状态管理
- 依赖代理主动读取和遵守，无强制执行机制
- 组件 token 属性有限（backgroundColor, textColor, typography, rounded, padding, size, height, width）

## 核心线索
- GitHub：https://github.com/google-labs-code/design.md
- 首发来源：GitHub Trending (TypeScript #1)
- 发布时间：2026年6月
- 当前状态：试验中（alpha）