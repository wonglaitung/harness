# GBrain — Brain-First 指令注入（组织级共享记忆 + 强制前置检索钩子）

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 把记忆问题从「存储/检索」重定位为**调用时机问题**：靠写进 harness 指令文件（CLAUDE.md / AGENTS.md）+ per-turn rule hook 强制「答前先查脑」，而非指望模型自觉调工具；并把「stable 通道 + 书面兼容性承诺 + 发布级 soak 测试（2 小时 / 60 万页）」引入记忆基础设施 |
| 采用广度 | ☆☆☆/5 | 官方适配 12+ harness：Claude Code、Codex（一条命令 wire memory/hooks/instructions）、OpenClaw、Hermes、opencode、Cursor、ChatGPT、Claude Desktop、Claude Cowork、Perplexity、Grok Build、Grok Bot、Muse、Windsurf（通用 stdio） |
| 时间新鲜 | ☆☆☆☆/5 | 2026 年在榜（stable 通道日更节奏），概念与工程承诺均为当期形态 |
| 社区热度 | ☆☆☆/5 | GitHub trending TypeScript 上榜（garrytan 个人高影响力项目），未见 HN 独立大讨论 |
| **总体判断** | ✅ | **新范式（记忆的调用时机层 + 组织级共享记忆治理）** |

## 技术定义 (What)
GBrain 是 MIT 许可、可自托管的「组织大脑」：个人笔记 + 公司文档（事实页 facts page、决策日志 decisions log、通话记录 call transcripts）进同一可检索库，再通过 `gbrain setup <harness>` 把一段「brain-first 指令块」写进 `~/.claude/CLAUDE.md` 或 Codex 的 `AGENTS.md`，并挂 per-turn rule hook。对外同时暴露 MCP server，供十余个客户端接入。默认零 API key（关键词检索起步，加 key 后升级语义检索）。

## 行业痛点 (Why)
Agent 记忆的真实失效点不是「存不下」，而是**「不会去取」**。MCP memory server、记忆文件、向量库都依赖模型主动决定「我该查一下」，实践中模型几乎不查，于是每个会话仍从零开始；同时个人记忆与公司记忆被割裂在各工具里，Claude Code 记的 Codex 不知道。

## 旧范式 vs 新范式
- **旧做法**：记忆 = 一个可选 MCP 工具 + 需模型自觉调用的检索接口；跨 agent 同步靠各自上下文。
- **新做法**：记忆 = 组织级基础设施 + **前置强制**。安装即写入 harness 指令文件并挂 per-turn hook，让「查脑」成为默认动作；一份脑经 MCP 对全部 agent 开放，构成跨 harness 单点事实源。发布侧叠加 stable 通道、书面兼容性承诺与 soak 测试。

## 生产力影响 (How)
- 新会话/新成员问「我们定价为什么这么定」可直接命中决策日志，减少重复交代背景的 token 与轮次。
- 跨 harness 统一事实源，消灭「A 工具记得、B 工具不知道」。
- 自托管 + MIT + 默认无 API key，给出企业可接受的记忆基础设施选项。

## 采用成本
- 自托管：Bun 1.4.4+，`bun install -g github:garrytan/gbrain#stable`（或 clone stable + `bun install && bun link`）；托管版 gbrain.io 付费可选。
- ⚠️ 官方明确警告：npm 上的 `gbrain` 是无关包且会遮蔽真实二进制，**不要** `npm install -g gbrain`；误装后用 `gbrain doctor` 修复。
- 真实成本在内容治理：脑的价值取决于团队是否真的把决策写下来。

## 采用案例
- 个人开发者：Claude Code / Codex 一条命令接入，笔记与公司文档统一检索。
- 团队：多 agent（Claude Code + Codex + Cursor + ChatGPT）共读同一脑，用于事实/决策类问答。

## 风险/局限
- 「强制前置检索」依赖指令文件与 hook 被正确写入并被 harness 尊重；不同 harness 对 hook 支持程度不一，能力可能退化。
- 默认关键词检索，语义召回需额外配置 API key。
- 自托管升级频繁（作者称一天多次发布），需主动固定版本；stable 通道的「兼容性承诺」需按其 docs/STABILITY.md 核对边界。

## 核心线索
- GitHub：https://github.com/garrytan/gbrain
- 首发来源：GitHub trending（TypeScript, daily）
- 发布时间：2026 年（stable 通道持续发布）
- 当前状态：活跃
