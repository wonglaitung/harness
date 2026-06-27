# DESIGN.md

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次为 AI 编码代理定义结构化视觉身份规范，YAML tokens + Markdown prose 双层格式 |
| 采用广度 | ☆☆☆/5 | Google Labs 官方出品，首日 2407 stars，已有 lint/diff CLI 工具链 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年6月首次公开发布 |
| 社区热度 | ☆☆☆☆/5 | GitHub Trending 首日 2407 stars，TypeScript 榜第一 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)
DESIGN.md 是一种格式规范，用于向 AI 编码代理（Claude Code、Codex、Cursor 等）描述项目的视觉身份。文件由两层构成：YAML front matter 提供机器可读的设计 token（颜色、字体、间距、圆角），Markdown body 提供人类可读的设计理念和适用说明。代理读取此文件后，能产出符合品牌规范的 UI 代码。

## 行业痛点 (Why)
AI 编码代理生成 UI 时缺乏设计一致性——每次生成颜色、字体、间距都随机，无法维持品牌视觉规范。传统方式依赖人类反复纠正，或把设计系统文档藏在 Figma/Storybook 中代理无法访问。

## 旧范式 vs 新范式
- **旧做法**：设计规范散落在 Figma、Storybook、CSS 变量文件中，AI 代理无法统一读取；每次生成 UI 需人工反复调整视觉细节
- **新做法**：项目根目录放置 DESIGN.md，AI 代理自动读取结构化 token + 语义说明，一次生成即符合品牌规范；支持 lint 校验和 diff 版本对比

## 生产力影响 (How)
开发者不再需要每次与 AI 对话时重复描述"用这个颜色、这个字体"。DESIGN.md 让代理持久理解设计系统，减少 UI 返工轮次。CLI 工具支持 WCAG 对比度检查和 token 级 diff，确保设计演进可追踪。

## 采用成本
- 时间：5-30 分钟编写 DESIGN.md（可从现有设计系统迁移）
- 金钱：免费开源（MIT 协议）
- 学习曲线：低——YAML + Markdown 格式，前端开发者零门槛

## 采用案例
- Google Labs 内部项目已使用
- 任何使用 Claude Code / Codex / Cursor 的团队均可集成
- 与 SPEC.md / AGENTS.md 形成项目规范三件套

## 风险/局限
- 目前版本为 alpha，token schema 可能变更
- 仅覆盖视觉身份，不包含交互逻辑和业务规则
- 依赖代理主动读取文件，需工具链配合

## 核心线索
- GitHub：https://github.com/google-labs-code/design.md
- 首发来源：GitHub Trending (TypeScript)
- 发布时间：2026年6月
- 当前状态：试验中（alpha）