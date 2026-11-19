# T3 Code — Agent Control Plane（跨 Agent 控制平面：一个服务端 + 全端同线程）

## 技术定义 (What)
T3 Code 把自己定位为 coding agents 的"控制平面"（control plane）而非又一个 agent：agent 仍在用户机器上跑、仍用用户自己的订阅（不转售 token），T3 只负责统一接口与状态。核心机制：单一服务端 + 桌面/Web/iOS/Android 多客户端共享同一批会话线程；可在会话中途切换模型、把任务从 Claude 交给 Codex；每个 thread 可独占一个 git worktree，审 diff 后一键 commit/push/PR；通过 ACP 协议接入 Claude Code、Codex、Cursor、OpenCode、Grok Build、Antigravity、Kiro、Pi 等任意 agent。

## 行业痛点 (Why)
Agent 数量爆发后，开发者面对的是碎片化：同一任务分散在五六个 CLI/TUI 里，"在工位起个头、离开后想批准下一步"做不到；换模型等于换工具、上下文与 diff 全部丢失；远程/移动端缺口只能靠 SSH。"哪个 agent 最强"的竞争，反而暴露了"没有一层能同时调度它们"的空缺。

## 旧范式 vs 新范式
- **旧做法**：把 agent 当成单一产品的内嵌能力（某个 IDE、某个桌面应用专有的 agent 面板）；换模型即换工具、会话不可迁移；跨设备只能靠 SSH 或干脆等回到桌面。
- **新做法**：把"控制"从"执行"里剥离出来做成独立一层：执行端（你机器上的各家用 agent）保持原样并可热插拔，控制端提供会话持久化、跨端同步、会话中途易主、per-thread worktree 与一键 PR。协议（ACP）而非适配器列表决定接入广度。

## 生产力影响 (How)
直接解决"人在移动、agent 在桌面"的真实工作流断点——手机上批下一步；同时让多 agent 协作变成默认而非手工搬上下文。MIT 授权 + 自托管，避免被单一 agent 厂商锁定，也为企业内多 agent 治理提供了可自控的落点。

## 采用成本
低。桌面端 brew/winget/scoop/yay/nix 多路可装，或 curl 一行脚本起服务、npx 免安装试用；前置仅需已有任一受支持的 agent 完成登录。远程需配 Tailscale 或 T3 Connect。

## 核心线索
- GitHub：https://github.com/pingdotgg/t3code
- 来源：https://github.com/trending/typescript?since=daily
- 发布时间：2026-11-19
