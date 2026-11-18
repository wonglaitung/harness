# OpenCode Browse — Tab Handoff 协议：把「人类持钥」做成 Agent 浏览的一等环节

## 技术定义 (What)
OpenCode Browse 是一个 MCP server + Chromium 扩展组合，让编码 Agent 直接使用用户**真实的**浏览器（保留标签页、登录态、扩展）。其核心创新不是「借用登录态」，而是把「何时必须交还控制权」显式建模为协议环节：Agent 在后台折叠标签组中打开标签、读页、点击、输入、截图、录屏；一旦遇到登录、2FA、支付等人类专属步骤，它把标签交还给用户，用户操作完后点 Continue，Agent 继续执行。另配套「Allowed sites」白名单约束 Agent 活动范围，以及「Lend a tab」把用户已开标签页主动借给 Agent。

## 行业痛点 (Why)
Agent 浏览的两难：让它用干净的无头浏览器，就撞上登录墙、2FA、反爬和「你已登录才可见」的内容；让它直接接管你的真实浏览器，又无法保证它不会在你不知情时动你的账号、花钱、或误操作。业界此前的解法是存储凭证（安全风险）或克隆 profile（易失效、违反 ToS），都没有解决「控制权在谁手上」这个问题。

## 旧范式 vs 新范式
- **旧做法**：Agent 使用独立的无头/隔离浏览器实例，凭证通过 cookie 注入、密钥托管或 profile 复制获得。人类与 Agent 的边界是「事先授权」——启动时给权限，之后 Agent 一路跑到底，人类只能在事后 review 结果。遇到登录墙就卡死或需要人工介入脚本。
- **新做法**：Agent 在用户真实浏览器里工作，但**控制权是分段交接的**：Agent 拥有「可自动化」段，人类保留「持钥」段（登录 / 2FA / 支付）。交接点是协议事件而非异常回退——Agent 主动 pause、把标签推回前台、用户点击 Continue 后 Agent 从同一点恢复。配合站点白名单，形成「Agent 可行动域」的显式契约。凭证从未离开人类手中。

## 生产力影响 (How)
对开发者意味着 Agent 自动化第一次能覆盖「登录后才能验证」的真实工作流：后台管理系统、需要 SSO 的内部工具、需 2FA 的第三方 SaaS、需支付确认的电商流程。这类场景此前占企业 Agent 落地失败案例的很大比例。同时把安全责任边界从「Agent 是否可靠」转为「交接点设计是否合理」，这是可审计、可辩护的设计。

## 采用成本
低。安装 Chrome 扩展后按引导完成配置，CLI 可选（curl / pwsh / npm / bun 四种方式）。兼容 Chrome、Edge、Brave、Arc、Helium、Vivaldi、Opera、Chromium。任何 MCP 客户端可用（OpenCode、Claude Code、Cursor、Codex、Zed）。无需存储 API key 或配置凭证。主要成本是用户需要接受「Agent 在自己的浏览器里活动」这一心智转变，以及为每个场景设计合理白名单。

## 核心线索
- GitHub：https://opencode.ai/product/browse
- 来源：https://news.ycombinator.com/ (HN 324 points, 2026-11-18)
- 发布时间：2026-11-18
