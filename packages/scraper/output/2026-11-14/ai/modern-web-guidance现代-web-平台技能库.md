# Modern Web Guidance（现代 Web 平台技能库）

## 技术定义 (What)
Modern Web Guidance 是一套「把 Web 平台专业知识编译成 Agent Skill」的技能库：由 Google Chrome、Microsoft Edge、Mozilla Firefox、MDN 四个团队共同维护，把 250 个现代 Web 特性（container queries、View Transitions、Popover API、Anchor Positioning、scheduler.yield、:has()、field-sizing…）连同浏览器兼容性数据和最佳实践，注入到编码 Agent 的上下文里。它通过 CLI 分发（`npx modern-web-guidance install` / `search` / `retrieve` / `legacy-scan`），并配有一套 eval dashboard——用评测来**剪掉模型已经知道的"最低公约数内容"**，从而让技能保持 token 高效。

## 行业痛点 (Why)
编码 Agent 默认产出 2019 年的代码。原因不是模型不知道新 API 存在，而是训练数据里充斥着海量遗留代码，且模型缺乏「现代实现模式的真实密度」。结果是：能用原生 CSS 一行解决的交互，Agent 生成上百行 JavaScript + 重型 polyfill。同时，模型若只是隐约知道 API 名字，往往会错误地组织调用方式。这是一个"知识的时效性与密度"问题，不是模型能力问题。

## 旧范式 vs 新范式
- **旧做法**：Web 最佳实践靠人来传播：MDN 文档、Chrome 开发者博客、caniuse 兼容表、Stack Overflow——都需要开发者主动检索并判断。Agent 侧的"补救"手段是笼统的 system prompt（"prefer modern APIs"）或 RAG 全量文档注入，前者无效、后者浪费上下文。
- **新做法**：Web 平台知识被**编译成可版本化、可评测、可剪枝的 Agent Skill**：四大浏览器/MDN 团队共同维护一份技能库，Agent 按需 `search`/`retrieve` 精准拉取单条指南进上下文，并且该技能的内容边界由 eval 决定——凡是模型已掌握的常识性内容被主动剪掉，只保留"模型会写错"的那部分。同时提供 `legacy-scan` 反向扫描存量代码库中的遗留模式。

## 生产力影响 (How)
产出代码从"能用 polyfill 跑"升级为"用浏览器原生能力跑"：更小的 bundle、更好的性能（浏览器可优化平台级 API）、内建可访问性。三个具体收益方向：①正确组织模型常误用的 API；②优先平台级 API 以获得浏览器优化与无障碍内建能力；③引导模型用轻量回退而非重型 polyfill。对团队而言，这是把"Web 平台最佳实践"从人的经验变成 Agent 的确定性输入。

## 采用成本
`npx modern-web-guidance@latest install` 一个交互式向导即可；也可不安装直接 `search`/`retrieve` 试用。学习成本接近零（对开发者透明）。真正成本在于组织层面：需要接受"由浏览器厂商团队来定义 Agent 该写什么 Web 代码"这一治理结构。

## 核心线索
- GitHub：https://github.com/GoogleChrome/modern-web-guidance
- 来源：https://github.com/trending/typescript?since=daily
- 发布时间：2026-11-14
