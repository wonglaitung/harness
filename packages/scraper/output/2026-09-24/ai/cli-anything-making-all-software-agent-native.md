# CLI-Anything — Making ALL Software Agent-Native

## 新范式评分
| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | "Agent-Native Software" + CLI-Hub 注册表，明确新术语与分发模型 |
| 采用广度 | ☆☆☆/5 | 18+ 应用 demo、ArcGIS/QGIS/Obsidian/n8n 等大量社区 CLI |
| 时间新鲜 | ☆☆☆☆☆/5 | 技术报告 arXiv:2606.03854（2026-06），news 活跃于 2026-04~05 |
| 社区热度 | ☆☆☆/5 | GitHub Trending Python，2461 通过测试，活跃 PR/issue 流水线 |
| 总体判断 | ✅ | 新范式（早期） |

## 技术定义 (What)
为任意软件生成 CLI harness 并注册到 CLI-Hub 的开放框架；配套 SKILL.md 技能文件，统一分发。

## 行业痛点 (Why)
专业软件无 agent 接口，GUI 自动化脆弱。Agent 生态缺乏"把长尾软件标准原生化"的机制。

## 旧做法 vs 新做法
- 旧做法：逐软件写 MCP server / GUI 脚本，无标准化入口
- 新做法：社区 CLI 注册表 + 技能文件，一处封装、全网 Agent 复用

## 生产力影响
数分钟让长尾专业软件可被 Agent 操作，提供 preview/trajectory 验证闭环。

## 采用成本
低（pip 安装 + PR 贡献）。

## 风险/局限
早期项目；CLI 质量依赖社区审查；对 GUI 复杂交互仍有限。

## 核心线索
- GitHub：https://github.com/HKUDS/CLI-Anything
- 技术报告：https://arxiv.org/abs/2606.03854
- 首发：2026-06（arXiv）
- 状态：活跃/试验中