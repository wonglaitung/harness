# Whiteboard — 人与 Agent 共同架构软件的画布 IDE

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 引入"diagram-that-leads-to-code"：Agent 用 SDK 在画布上以图为第一公民沟通，颠覆纯文本 Agent 交互 |
| 采用广度 | ☆☆☆/5 | 支持 Claude Code、Codex 等主流 agent；YC W26 背书；MIT 开源 |
| 时间新鲜 | ☆☆☆☆☆/5 | YC W26 项目（2026 冬季），首发 < 6 个月 |
| 社区热度 | ☆☆☆☆/5 | HN 170 分 + Show HN 170 分，YC 孵化 |
| **总体判断** | ✅ | **新范式——Agent 可视化沟通媒介** |

## 技术定义 (What)
一个开源的桌面画布 IDE，让人类与 coding agent 在共享工作区共同架构软件。Agent 通过 SDK 在画布上绘制流程图、序列图、ER 图，可视化点击跳转底层代码。

## 行业痛点 (Why)
AI 编程瓶颈从"生成"转向"理解"：纯文本工具无法连接 spec/架构图与代码，tradeoff 常实现后才暴露，raw diff 噪声大，人类无法理解 Agent 的自主决策。

## 旧范式 vs 新范式
- **旧做法**：Agent 纯文本 TUI 输出 + raw diff 审查，架构意图淹没在噪声中
- **新做法**：图作为第一公民——语义 AST 感知 diff、决策日志可视化、点击图跳转代码

## 生产力影响 (How)
将"理解"工程化：Agent 工作产物可视化，大幅降低 review 复杂 Agent 改动的认知负担。

## 采用成本
MIT 开源、本地运行，即装即用；需改变人机协作习惯。

## 风险/局限
- 当前不能编辑文件、多 repo 审查支持弱（官方已知局限）
- 依赖 Agent 输出质量，画布只是呈现层

## 核心线索
- GitHub：https://github.com/devdotfast/whiteboard
- 首发来源：Show HN（YC W26）
- 发布时间：2026-09-24
- 当前状态：早期（活跃）