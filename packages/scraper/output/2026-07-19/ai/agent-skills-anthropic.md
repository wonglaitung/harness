
# Agent Skills — Agent能力扩展的开放标准协议

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首次定义"Skill=文件夹+SKILL.md"作为Agent能力的标准载体，引入渐进式披露(Progressive Disclosure)三阶段加载机制 |
| 采用广度 | ☆☆☆☆☆/5 | 30+客户端/平台已支持：Claude Code, Gemini CLI, OpenAI Codex, VS Code, JetBrains Junie, Databricks, Snowflake Cortex, Roo Code, Kiro, Amp, Letta, Spring AI, OpenHands, Pulumi Neo, Tabnine 等 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2025年中首发，2025年7月Anthropic官方仓库开源，生态爆发中 |
| 社区热度 | ☆☆☆☆/5 | GitHub 312 stars/day (anthropics/skills)，agentskills.io独立规范站，Notion已发布Partner Skill |
| **总体判断** | ✅ | **新范式 — Agent能力的事实标准协议** |

## 技术定义 (What)

Agent Skills 是一种轻量级开放格式，用于扩展 AI Agent 的专业能力。核心载体是一个包含 `SKILL.md` 文件的文件夹，其中 YAML 前置元数据（name + description）定义技能身份，Markdown 正文定义执行指令。Skills 可捆绑脚本、模板、参考资源等。

关键机制是**渐进式披露（Progressive Disclosure）**三阶段加载：
1. **Discovery**：启动时仅加载 name + description，极小上下文开销
2. **Activation**：任务匹配时加载完整 SKILL.md 指令到上下文
3. **Execution**：按需执行捆绑代码或加载引用文件

## 行业痛点 (Why)

当前 Agent 缺乏可移植的能力封装标准：
- 每个平台（Claude Code、Cursor、Codex等）各自定义工具/插件格式，互不兼容
- Agent 的领域专业知识无法跨平台复用
- 企业工作流（法务审查、数据分析、品牌规范）无法以可版本控制的方式打包给 Agent
- Prompt Engineering 缺乏可组合、可审计、可分发的标准单元

## 旧范式 vs 新范式

- **旧做法**：每个 Agent 平台定义私有工具/插件格式（如 OpenAI Functions、MCP Tools），能力绑定平台，无法跨平台复用；专业知识靠 system prompt 硬编码，冗长且不可组合
- **新做法**：Skills 以文件系统为基础（文件夹+SKILL.md），Git 原生版本控制，任何支持规范的 Agent 都可加载；渐进式披露使 Agent 可同时持有数百个技能而不膨胀上下文；一次编写，Claude Code / Gemini CLI / Codex / VS Code 全平台复用

## 生产力影响 (How)

- **技能复用**：企业一次编写品牌规范 Skill，所有兼容 Agent 即时获得能力
- **可审计性**：SKILL.md 是纯文本，可 Git 追踪、Code Review、CI 验证
- **上下文效率**：渐进式披露让 Agent 持有 100+ 技能而不占用推理 token
- **生态飞轮**：Partner Skills（Notion 已首发）开启"技能市场"模式
- **Claude Code Plugin Marketplace**：`/plugin marketplace add anthropics/skills` 一键安装技能包

## 采用成本

- **学习成本**：极低 — 一个 SKILL.md 文件即可创建技能，YAML 前置元数据仅需 name + description
- **时间成本**：5 分钟创建基础 Skill，30 分钟创建含脚本和资源的完整 Skill
- **迁移成本**：零 — 纯增量式采用，无需替换现有工具链
- **兼容性**：与 MCP 互补而非竞争，MCP 提供 Agent 工具调用接口，Skills 提供 Agent 知识/工作流指令

## 采用案例

- **Anthropic 官方 Skills**：文档生成（docx/pdf/pptx/xlsx）、MCP Server 生成、Web 测试、品牌通讯等
- **Notion Partner Skill**：Notion 官方发布 Claude Skill，教 Agent 如何使用 Notion API
- **Code with Claude Workshops**：8 个官方工作坊全部基于 Skills 构建（rightmodel, agent-decomposition, eval-driven-agent-development 等）
- **Claude Code Plugin Marketplace**：anthropics/skills 作为首个技能市场仓库

## 风险/局限

- **规范碎片化风险**：agentskills.io 是开放标准，但 Anthropic 实现可能成为事实标准，其他厂商的实现程度待观察
- **执行安全**：Skills 可捆绑可执行脚本，需沙箱化运行环境
- **质量参差**：开放生态下 Skill 质量无强制审核，可能产生低质量或误导性技能
- **与 MCP 的边界**：Skills（知识/工作流指令）vs MCP（工具调用接口）的分工仍在演进中

## 核心线索

- GitHub：https://github.com/anthropics/skills
- 规范站：https://agentskills.io
- Anthropic 工程博客：https://anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- 首发时间：2025年中
- 当前状态：🔥 爆发中 — 30+ 客户端支持，生态快速扩张
