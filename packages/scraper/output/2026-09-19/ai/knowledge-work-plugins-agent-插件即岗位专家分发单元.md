# Knowledge Work Plugins — Agent 插件即岗位专家分发单元

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 把 Agent 能力打包成"插件"单元：skills + connectors + slash commands + sub-agents，纯 markdown/JSON、零代码、零构建 |
| 采用广度 | ☆☆☆/5 | Anthropic 官方开源 11 个插件（销售/法务/财务/数据/客服等），接入 Claude Cowork + Claude Code |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026-09 随 Claude Cowork 首发 |
| 社区热度 | ☆☆☆☆/5 | GitHub 单日 +300 stars，Anthropic 官方背书 |
| **总体判断** | ✅ | **新范式（分发/生态层）** |

## 技术定义 (What)
Knowledge Work Plugins 把"某个岗位的完整 AI 工作方式"打包成一个可安装、可自定义的插件单元：`plugin.json`（manifest）+ `.mcp.json`（连接器）+ `commands/`（斜杠命令）+ `skills/`（领域知识）。全部是 markdown 和 JSON 文件，无代码、无基础设施、无构建步骤。

## 行业痛点 (Why)
此前给 Agent 注入领域能力靠零散的 system prompt、手写 skill、逐个接 MCP server。经验无法复用、无法在公司内标准化分发。插件把"如何做好这份工作"变成可版本化、可共享、可定制的包。

## 旧范式 vs 新范式
- **旧做法**：每个团队各自拼 prompt + skill + MCP 连接，能力碎片化、经验不可迁移
- **新做法**：以"插件"为最小分发单元，一站式打包技能/连接器/命令/子代理，从 marketplace 安装、按公司定制

## 生产力影响 (How)
一个岗位开箱即用（如 `/sales:call-prep`、`/data:write-query`），管理员用共享插件统一团队工作方式，少花时间"教" AI、多花时间改业务。

## 采用成本
零代码（全 markdown/JSON），安装即用；真正价值在于"按公司定制"——换连接器、加术语、改流程，需要一次性的组织投入。

## 采用案例
- Anthropic 官方开源 11 个岗位插件（productivity/sales/legal/finance/data/enterprise-search/bio-research 等）
- 每个插件标注开箱连接器（如 sales → HubSpot/Clay/ZoomInfo）

## 风险/局限
- 与 Anthropic 生态（Claude Cowork/Code）强绑定，跨平台标准尚待形成
- 本质是"知识工程 + 分发"，概念创新偏生态层而非底层技术
- "即用插件"只是起点，真正收益取决于定制深度

## 核心线索
- GitHub：https://github.com/anthropics/knowledge-work-plugins
- 首发来源：Claude Cowork 发布（2026-09）
- 关联：Claude Code plugin marketplace