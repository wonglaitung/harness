# DESIGN.md — Agent设计系统规范

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次定义"Agent可读的设计系统规范"，YAML token + Markdown rationale双层结构 |
| 采用广度 | ☆☆☆/5 | Google官方发布，504⭐/天，配套CLI工具 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年6月首发 |
| 社区热度 | ☆☆☆☆/5 | GitHub 504⭐/天，快速增长 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)
DESIGN.md是一种机器可读的设计系统描述格式，将YAML front matter中的设计token（颜色、字体、间距、圆角、组件）与Markdown正文中的设计理念结合，让AI编码Agent能持久理解并一致执行视觉设计规范。

## 行业痛点 (Why)
AI编码Agent（Claude Code、Codex等）在生成UI时缺乏设计一致性——每次生成都是"从零开始"，无法维持品牌视觉规范。现有的DESIGN.md（类似README.md）只是给人看的，Agent无法结构化消费。

## 旧范式 vs 新范式
- **旧做法**：设计师出Figma/Sketch文件 → 开发者手动翻译为CSS → Agent无法消费设计系统
- **新做法**：DESIGN.md作为Agent可读的设计规范 → Agent直接消费token生成一致UI → `npx @google/design.md lint`验证合规性

## 生产力影响 (How)
开发者不再需要反复向Agent解释"用这个颜色、这个字体"——一次定义，所有Agent会话自动遵循。配套的lint工具可检测WCAG对比度、token引用错误、设计回归。

## 采用成本
- 学习曲线：低（YAML+Markdown，5分钟上手）
- 时间成本：约30分钟编写首个DESIGN.md
- 金钱成本：免费（开源MIT）

## 采用案例
- Google内部：作为Agent设计规范标准
- 任何使用Claude Code/Codex的团队：将DESIGN.md放入项目根目录

## 风险/局限
- 目前为alpha版本规范，可能变动
- 仅覆盖视觉设计，不涉及交互逻辑
- 依赖Agent主动读取和遵循，无强制执行机制

## 核心线索
- GitHub：https://github.com/google-labs-code/design.md
- 首发来源：Google Labs Code
- 发布时间：2026年6月
- 当前状态：试验中（alpha）