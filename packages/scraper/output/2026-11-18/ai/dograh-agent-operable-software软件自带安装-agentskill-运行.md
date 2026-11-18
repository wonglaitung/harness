# Dograh — Agent-Operable Software（Install-by-Agent）

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 「skill 不硬编码步骤、运行时读产品自己的脚本与文档」这一招是新的分发契约；`doctor.sh` 输出机器可判定三态 + 非零退出码，把「可诊断性」做成对外接口 |
| 采用广度 | ☆☆/5 | 目前主要是 Dograh 自身在实践（dograh-hq/dograh-plugins）；尚未见到其他自托管项目跟进同一模式，属早期 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026-11 新发布；Product Hunt 日榜/周榜/月榜 #1 |
| 社区热度 | ☆☆☆/5 | Product Hunt 三榜第一 + Trendshift 收录 + Better Stack 实测视频；但 GitHub 当日仅 +17 star，HN 未上榜——热度在产品侧，不在开发者侧 |
| **总体判断** | ⚠️ | **观察中，但方向明确**：概念创新 + 时间新鲜成立，采用广度尚不足 |

## 技术定义 (What)
Dograh 是开源自托管（BSD 2-Clause）的语音 Agent 平台，对标 Vapi / Retell：可视化工作流编排、内置 telephony（Twilio/Vonage/Telnyx/Plivo/Asterisk ARI）、自带 LLM/TTS/STT 栈、可整体换成自己的 provider，一条 Docker 命令起，且自带 MCP server 让编码 Agent 能直接创建/编辑语音工作流。

但范式层面的新意在分发端：官方插件里 `dograh-setup` skill 明确「先侦察（OS、已装什么、部署还是开发、全新还是复用已有 Postgres/Redis/S3），然后**去读并驱动 Dograh 自己的 setup 脚本与文档，而不是硬编码步骤**——这样产品变化时 skill 仍保持最新」。配套 `doctor.sh` 一次性诊断前置条件、容器状态、端口、`/api/v1/health`、UI、`.env`，输出 `[OK]/[WARN]/[FAIL]` 并附修复提示，出问题时返回非零退出码。

## 行业痛点 (Why)
1. 自托管基础设施的 N×M 组合（本地/远程 × Docker/裸机 × 全新/复用已有服务）无法用文档穷举，文档必然滞后；
2. 用户卡住时只能把报错复制给 LLM，而 LLM 不知道现场状态；
3. 既往的 Agent skill 把步骤硬编码进 SKILL.md，产品一升级 skill 就撒谎——这类 skill 腐化速度比文档还快。

## 旧范式 vs 新范式
- **旧做法**：产品输出人读文档，人手工执行；Agent skill 内置固定命令序列，产品变更后即失效；健康检查靠人看日志判断。
- **新做法**：产品同时向 Agent 交付「侦察 → 读真源 → 执行 → 三态诊断」的闭环。skill 是**驱动器**而非**副本**，因此不会腐化；doctor 输出是契约，Agent 可直接据其决策。

## 生产力影响 (How)
- 对采用者：部署一套完整语音栈（含 WebRTC 音频、公网 telephony webhook、对象存储）从半天降到几分钟的对话，且支持「半途失败后不删卷恢复」。
- 对生态：给出了可复制的模板——复杂自托管产品的标准交付形态可能变成「容器 + MCP server + setup skill + doctor 脚本」四件套。
- 附带价值：MCP server 让「用自然语言设计语音工作流」成为默认交互，降低 voice agent 的构建门槛。

## 采用成本
- 使用方：需要 Claude Code / Codex（插件市场一条命令），平台本体 `curl` 一条 Docker 命令；可用云版本规避自托管。
- 维护方（关键成本）：setup 脚本、文档、doctor 三者必须与代码同步，否则 Agent 会被误导；这是新增的工程纪律负担。

## 采用案例
- **Dograh 自身**：默认启动即拉起完整栈（含 `*.trycloudflare.com` 隧道以便接 telephony webhook），无 API Key 也能对话测试——降低了「Hello World」门槛。
- **Better Stack**：公开实测视频，属于第三方验证。

## 风险/局限
- **热度错配**：Product Hunt 三榜第一但 GitHub 日增仅 +17 star，说明「营销热」尚未转化为开发者采用；采用广度维度目前不成立。
- **版本范围窄**：插件 v1 只覆盖安装与排障，telephony 配置与压测仍是 roadmap。
- **依赖闭源 harness**：setup 能力绑定 Claude Code / Codex 的插件机制，非这两者的用户拿不到收益。
- **隐私**：默认收集匿名使用数据（需 `ENABLE_TELEMETRY=false` 关闭），且默认开启注册 + 公网隧道，自托管安全默认值偏松，需自行收紧。

## 核心线索
- GitHub：https://github.com/dograh-hq/dograh
- 插件仓库：https://github.com/dograh-hq/dograh-plugins
- 文档：https://docs.dograh.com
- 首发来源：GitHub Trending (Python, daily) + Product Hunt #1
- 发布时间：2026-11
- 当前状态：活跃，实验性扩张中
