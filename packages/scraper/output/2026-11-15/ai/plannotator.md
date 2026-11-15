# Plannotator

## 技术定义 (What)
Plannotator 是面向编码 Agent 的本地浏览器"评审面（review surface）"：通过插件、hooks 和命令直接嵌入 Claude Code、Codex、Copilot CLI、Gemini CLI、OpenCode、Kiro、Droid、Amp、Pi 等 Agent；当 Agent 提出计划、决策、HTML 制品或完成工作时，自动在浏览器打开对应产物，人可以在上面标注意见、评论 diff/PR，再把结构化反馈直接回传给 Agent 执行。新增的 Plannotator Inbox 是"人与多 Agent 协作之间的缺失评审层"，把决策、原型、变体、计划汇聚成一个待审收件箱。

## 行业痛点 (Why)
Agent 从"写代码"升级为"提计划、出制品、并行多个 Agent 干活"后，人失去了介入点：计划只存在于终端滚动的文本里，多 Agent 的产出散落在各分支/终端窗口，代码 diff 之外的原型与方案无人审。终端是 Agent 的输出端，却不是人的输入界面——反馈只能靠打字复述，信息损耗大、无法指向具体位置。

## 旧范式 vs 新范式
- **旧做法**：在终端里读 Agent 的长文本计划，用自然语言"打回重做"；代码评审在 GitHub PR 里做，与 Agent 的实时工作流割裂；制品（HTML/原型）靠截图互传。人只能看最终 diff，无法在"计划阶段"低成本纠偏。
- **新做法**：Agent 输出自动升级为"可批注制品"，人用标注而非描述来反馈——评审发生在产物本身的坐标上（某一行、某个组件、某段计划），并以结构化形式回流给 Agent。浏览器成为 Agent 的通用人机接口，一个 Inbox 统一对多 Agent、多类型制品（计划/spec/markdown/HTML/diff/PR）进行收件箱式分诊。工具无关（tool-agnostic）：同一层服务所有 Agent CLI。

## 生产力影响 (How)
1) 把"计划审批"从数分钟的文字往返压缩为一次标注，纠偏发生在动手写代码之前，返工成本显著下降；2) 多 Agent 并行时的调度开销从"记住每个终端在干什么"变为一个待审收件箱；3) diff 之外的抽象产物（设计、spec、原型）第一次进入可评审闭环；4) 反馈结构化后可直接驱动 Agent 行动，减少"人说完、Agent 猜错"的循环。

## 采用成本
低。本地运行、浏览器 UI，按 Agent 装对应插件/hook 即可；已在 README 中列出 10+ Agent 的官方支持图标，可渐进采用（先只用 plan review，再扩到 code review / Inbox）。主要成本是团队接受在浏览器里做评审的习惯改变。

## 核心线索
- GitHub：https://github.com/plannotator/plannotator
- 来源：https://github.com/plannotator/plannotator
- 发布时间：2026-11-15
