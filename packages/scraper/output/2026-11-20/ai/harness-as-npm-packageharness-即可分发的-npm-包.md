# Harness-as-npm-Package（Harness 即可分发的 npm 包）

## 技术定义 (What)
把编码 Agent 的 harness 拆成一组可独立安装、可组合、可通过 npm/git 分发的包：permissions、telemetry 契约、durable 运行时、agent core、TUI、coding-agent CLI 各自独立成包，用户用 extensions / skills / prompt templates / themes 组装出"自己的" harness，并以 "Pi package" 形式分享。

## 行业痛点 (Why)
现有编码 Agent（Claude Code、Codex、Cursor）把 harness 做成封闭产品：sub-agent、plan mode、权限模型全部内建且不可拆，团队想改工作流只能等厂商排期，或 fork 整个单体仓库。harness 的差异（而非模型能力）越来越决定产出质量，却没有分发机制。

## 旧范式 vs 新范式
- **旧做法**：Harness = 厂商交付的单体二进制；定制 = 写配置文件或提 feature request；换 harness = 换整个产品（连同账号、订阅、键位习惯一起迁移）。
- **新做法**：Harness = 可组装的包集合，且刻意"跳过" sub-agents 与 plan mode——把这两者降级为可选包而非默认功能。核心理念反转为「Adapt Pi to your workflows, not the other way around」。同时通过 OpenClaw 等真实集成验证：harness 可以被第三方应用当作 SDK/库嵌入（TypeScript SDK + RPC 模式），而非只能作为终端黑盒使用。

## 生产力影响 (How)
团队可以把内部规范（PR 流程、测试门槛、部署检查）压成一个 npm 包分发给全员，Agent 行为随包版本升级而统一；不同业务线可安装不同 harness 组合而不污染彼此。为"Agent 工程"提供了类似 ESLint preset / Vite plugin 的复用生态位。

## 采用成本
中低：Node.js 22.19+，一条 curl 脚本安装；学习成本在于理解包组合模型（extensions/skills/templates/themes）。风险：默认不带权限系统（按启动用户权限运行），生产环境必须自行容器化/沙箱化——这是明确写在 README 里的取舍。

## 核心线索
- GitHub：https://github.com/earendil-works/pi
- 来源：https://github.com/trending/typescript?since=daily
- 发布时间：2026-11-20
