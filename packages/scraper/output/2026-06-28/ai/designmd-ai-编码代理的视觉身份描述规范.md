# DESIGN.md — AI 编码代理的视觉身份描述规范

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首次定义"设计规范即代码"供 AI 代理消费的标准格式，YAML token + Markdown 理念双结构 |
| 采用广度 | ☆☆☆☆/5 | GitHub Trending #1 (1541 星/天)，Google 官方背书，配套 CLI 工具链完整 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2025年6月首次发布，当前 alpha 版本 |
| 社区热度 | ☆☆☆☆/5 | GitHub 日增 1541 星，Google Labs 出品 |
| **总体判断** | ✅ | **新范式 — AI 编码代理的设计规范标准** |

## 技术定义 (What)
DESIGN.md 是一种 Markdown 格式规范，在 YAML front matter 中定义机器可读的设计 token（颜色、排版、间距、圆角、组件），在 Markdown 正文中描述设计理念和应用规则。AI 编码代理读取此文件后，可持久理解并忠实执行项目的视觉系统。

## 行业痛点 (Why)
AI 编码代理（Claude Code、Codex、Cursor）在生成 UI 代码时缺乏对设计系统的持久理解。开发者每次对话都需重复描述颜色、字体、间距，且 AI 容易偏离品牌一致性。口头描述或截图参考不可靠、不可版本化、不可复用。

## 旧范式 vs 新范式
- **旧做法**：在 prompt 中反复描述设计偏好，或依赖截图/Figma 让 AI 猜测设计意图，每次会话重新传达视觉规范
- **新做法**：项目根目录放置 DESIGN.md，AI 代理自动读取并持久理解设计系统。支持 lint 验证、diff 回归检测、export 导出 Tailwind/DTCG 格式

## 核心特性
1. **双结构设计**：YAML token 给代理精确值，Markdown prose 告诉代理"为什么"
2. **完整工具链**：`lint`（验证结构+WCAG对比度）、`diff`（检测 token 级回归）、`export`（输出 Tailwind v3/v4、DTCG 格式）
3. **组件化 token**：支持 `{colors.primary}` 引用语法，组件变体（hover/active/pressed）
4. **规范注入**：`npx @google/design.md spec --rules` 可将规范注入代理 prompt

## 生产力影响 (How)
- 消除重复描述设计规范的时间消耗
- AI 生成 UI 代码自动遵循品牌视觉系统，减少审查轮次
- 设计变更可通过 diff 命令自动检测回归
- 设计规范版本化、可团队共享

## 采用成本
- 极低：创建 DESIGN.md + `npx @google/design.md lint`
- 与 Tailwind、W3C DTCG 生态兼容
- 学习曲线平缓，格式直观

## 采用案例
- Google Labs 内部项目已采用
- 可与 Claude Code、Codex、Cursor 等所有主流 AI 编码代理配合使用
- 通过 `spec --rules` 命令可注入任意代理的 prompt

## 风险/局限
- 当前版本为 alpha，格式可能变动
- 需要代理主动读取文件（依赖代理能力）
- 尚无 IDE 插件支持可视化编辑

## 核心线索
- GitHub：https://github.com/google-labs-code/design.md
- 首发来源：GitHub Trending
- 发布时间：2025年6月
- 当前状态：alpha，活跃开发中