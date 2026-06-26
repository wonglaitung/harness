
# DESIGN.md

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首次定义"给AI编码Agent描述视觉身份"的标准化格式规范，YAML front matter + Markdown双层结构 |
| 采用广度 | ☆☆☆/5 | Google Labs官方出品，W3C DTCG互操作，Tailwind v3/v4导出支持 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年6月首发，GitHub Trending #1 (2319⭐/day) |
| 社区热度 | ☆☆☆☆☆/5 | 单日2319 stars，GitHub Trending全站第一 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)
DESIGN.md 是一种格式规范，用于向AI编码Agent（Claude Code、Codex、Cursor等）描述项目的视觉身份。文件由YAML front matter（机器可读的设计token：颜色、排版、圆角、间距、组件）和Markdown正文（人类可读的设计理念阐述）组成，类似于README.md描述项目信息，DESIGN.md描述项目外观。

## 行业痛点 (Why)
AI编码Agent生成UI时缺乏持久的设计上下文——每次生成风格不一致，需要反复用自然语言描述"品牌调性"。传统设计token格式（如Figma Token、Style Dictionary）面向人类设计师和构建工具，Agent无法直接理解。

## 旧范式 vs 新范式
- **旧做法**：在prompt中用自然语言描述设计偏好，或维护分散的CSS变量/Tailwind配置，Agent无法系统性地理解设计意图
- **新做法**：项目根目录放置DESIGN.md，Agent自动读取YAML token获得精确设计值，同时读取Markdown理解设计理念，生成一致UI

## 生产力影响 (How)
开发者不再需要在每次Agent交互中重复描述设计偏好。Agent一次读取DESIGN.md即可持续产出风格一致的UI。内置lint检查WCAG对比度、token引用完整性，diff命令检测设计回归——从"手动审校Agent UI输出"升级为"Agent自动遵循设计系统"。

## 采用成本
- 时间：5-30分钟编写DESIGN.md（可从现有设计系统迁移）
- 学习曲线：低（YAML + Markdown，开发者熟悉）
- 集成：`npm install @google/design.md`，一条命令lint

## 采用案例
- 任何使用AI编码Agent的项目：根目录放置DESIGN.md，Agent自动读取
- 支持 Tailwind v3/v4 配置导出、W3C DTCG标准导出
- CLI提供 `lint`（校验）、`diff`（对比两个版本）、`export`（导出为多格式）

## 风险/局限
- 当前版本为 alpha，格式可能变更
- 需要AI编码Agent生态主动支持读取DESIGN.md
- 目前仅面向Web前端设计token，未覆盖3D/游戏等场景

## 核心线索
- GitHub：https://github.com/google-labs-code/design.md
- npm：@google/design.md
- 首发来源：GitHub Trending
- 发布时间：2026年6月
- 当前状态：活跃（alpha）
