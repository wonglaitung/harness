# Stitch Design Skills — 设计⇄代码双向回环（Design-of-Record）

## 技术定义 (What)
Google Labs 的 Agent Skills 库，把 Google Stitch 变成一个由 MCP 驱动的「设计注册中心」，并首次把**设计语言的提取与再生成做成双向闭环**：(1) **code → design**：`extract-design-md` 从 `/src` 反向抽取 `DESIGN.md`（设计语言即文本制品）；`code-to-design` 把运行中的前端代码经「HTML 提取 + 设计系统 + 上传」灌回 Stitch 项目；`extract-static-html` 抓取运行中应用的静态快照。(2) **design → code**：`react-components` / `react-native` / `react-vite-dashboard` 把 Stitch 屏幕转成组件系统，并带**自动校验与 design token 一致性检查**。(3) 最关键的动词是 **`sync`**——「把应用同步到 Stitch 项目的最近一次更新」。这意味着设计项目被当作**持久的上游真相（Design-of-Record）**，代码是可反复重新派生的下游制品，而不是一次性生成物。所有 skill 遵循 Agent Skills 开放标准，跨 Codex / Claude Code / Cursor / Gemini CLI / Antigravity / OpenCode 安装。

## 行业痛点 (Why)
「设计→代码」的 AI 工具几乎都是单向一次性生成：生成完代码，设计稿立刻过时，下一轮修改只能靠人肉在代码里猜设计意图。同时设计系统（token、字体、间距）分散在设计文件与源码两处，永远不同步。

## 旧范式 vs 新范式
- **旧做法**：设计稿是一次性输入，代码是终态产物；设计系统靠人写文档、靠人肉对齐。
- **新做法**：设计项目是**可寻址的上游真相**，代码是可在任意时刻 `sync` 重新派生的下游；`DESIGN.md` 作为设计语言的双向交换格式，既能从代码抽取，也能回灌设计系统。UI 代码从「一次性生成物」变成「可重复收敛的派生视图」。

## 生产力影响 (How)
多轮迭代场景下，设计意图不再在代码里腐化：改设计 → re-sync → 组件重新生成并自动校验 token 一致性。UI 迁移（同一设计投射到 Web / RN / Dashboard 三种目标）从三份手写变成一次设计 + 三次派生。

## 采用成本
中。需配置 Stitch MCP server 与凭据；skill 之间有依赖，选择性安装需自行补齐。OpenCode 需手动拷目录并改 kebab-case 命名。

## 核心线索
- GitHub：https://github.com/google-labs-code/stitch-skills
- 来源：https://github.com/google-labs-code/stitch-skills
- 发布时间：2026-11-18
