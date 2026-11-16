# agweb — 永不抢焦点的 Agent 专用浏览器

## 技术定义 (What)
agweb 是 macOS 上基于 WebKit 构建的「编码 Agent 专用浏览器」：一个永不抢占键盘焦点的真实窗口，多个 Agent 通过 playwright-cli 风格的 shell 命令（`agweb`）各自驱动独立 workspace 与标签页，人类通过 dashboard 同时实时观看所有 Agent 的操作。

## 行业痛点 (Why)
并行运行多个编码 Agent 时，Playwright 的 Chrome 窗口不断抢走用户键盘焦点；headless 浏览器则被部分站点封锁、且出错时无从观察。Chrome 的 GPU 进程在五个空闲页时占住 5-7 个核心。

## 旧范式 vs 新范式
- **旧做法**：Agent 浏览器要么是 headless（不可见、被反爬封锁、调试黑箱），要么是 Playwright 驱动的有头 Chrome（抢焦点、资源重、多 Agent 无法隔离、登录态无法共享）。
- **新做法**：「**永不抢焦点的真实窗口**」+「**每 Agent 独立 workspace**」。窗口始终真实存在（绕过 headless 检测），但永不前置；空闲标签页先降频后挂起（5 个空闲页 0% CPU / 590MB）。交互差异以 diff 形式回报，Agent 无需二次快照。共享命名 profile 让多 Agent 并发复用同一登录态。

## 生产力影响 (How)
多 Agent 并行从「互相打断 + token 爆炸」变为可观测的流水线：动作回复直接说明改了什么（省去每步 snapshot），refs 在元素存活期间保持稳定，`fill --secret-cmd` 让密码不进 transcript。人类保留 `ask` 移交能力处理登录/MFA/CAPTCHA。

## 采用成本
低。需 macOS 26+（Apple silicon 或 Intel），下载 dmg 或从源码构建（Xcode 26+）；一条命令 `agweb install-skill` 即接入 Claude Code / Codex。局限是 WebKit-only，无 CDP，Chrome 扩展不可用。

## 核心线索
- GitHub：https://github.com/paul-nameless/agweb
- 来源：https://github.com/paul-nameless/agweb
- 发布时间：2026-11-16
