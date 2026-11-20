# Harness-Portable Plugin Compilation（跨 Harness 插件编译：Markdown 单一真源 + 适配器生成 + CI 校验能力降级）

## 技术定义 (What)
把 agent 的插件/agent/skill/command 只写一份（Claude Code 插件格式的 Markdown），由 tools/adapters/ 下的适配器编译成每个 harness（Claude Code、Codex CLI、Cursor、OpenCode、Antigravity CLI、GitHub Copilot、Pi）各自能读的格式；适配器同时负责把模型别名映射到该 harness 的模型、把工具权限做翻译，CI 每次重新生成并做结构校验 + 在已安装的真 CLI 里跑通。

## 行业痛点 (Why)
Agent 生态已经碎片化成 7+ 个互不兼容的 harness（Claude Code / Codex CLI / Cursor / OpenCode / Antigravity / Copilot / Pi）。同一套 prompt、skill、命令每换一个工具就要重写一遍，而且各家的模型命名、权限模型、组件类型（agent 还是 skill 还是 prompt template）都不一样，维护成本随 harness 数量线性上升。

## 旧范式 vs 新范式
- **旧做法**：一套 prompt/skill 绑定一个 harness，仓库按工具分叉（xxx-for-claude、xxx-for-cursor），靠人工同步；换工具等于重写。
- **新做法**：单一 Markdown 真源 + 适配器代码生成的「编译」模型：贡献者只写 Claude Code 插件格式，适配器按目标 harness 的能力矩阵做有损/无损转换（command → skill 或 prompt template；agent 格式按 harness 改写；opus/sonnet/haiku/inherit 别名映射到各家模型；工具权限按各家支持度翻译），并由 CI 强制重新生成 + 校验 + 用真 CLI 执行验证。分发单位从「某个工具的插件」变成「跨工具的能力包」。

## 生产力影响 (How)
一次编写，7 个 harness 同时可用：仓库内 93 个插件（91 本地 + 2 外部）、199 个 agents、185 个 skills、103 个 commands 全部由同一份源码生成。对团队的直接价值是消除 N×M 维护矩阵（N 个能力 × M 个工具），并让「能力在哪个工具上缺失/降级」变成可查询的 capability matrix，而不是踩坑后才知道。

## 采用成本
中：需要接受 Claude Code 插件格式作为源格式（等于把一家格式当 IDL）；贡献者要装 make/uv 工具链并在提交前跑 make generate-all + make validate STRICT=1。适配器的模型别名映射与权限翻译需要随各 harness 版本持续维护（这是持续成本，不是一次性）。

## 核心线索
- GitHub：https://github.com/wshobson/agents
- 来源：https://github.com/trending/python?since=daily
- 发布时间：2026-11-20
