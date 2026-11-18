# Claude Trading Skills — 决策门控工作流清单（Decision-Gate Workflow Manifest）

## 技术定义 (What)
一套面向散户投资者的 Claude Code / Agent Skills 工具包，核心不是「让 AI 选股」，而是把投资流程写成机器可读的 YAML workflow manifest：每个 manifest 依次列出该流程所需的 skills、决策闸门（decision gates）和产出物（artifacts）。例如 `swing-opportunity-daily` 强制顺序为 vcp-screener → drawdown-circuit-breaker → technical-analyst → position-sizer → trader-memory-core → pre-trade-discipline-gate，且每个 workflow 声明自己的 API profile（必需数据源 / 降级方案）。

## 行业痛点 (Why)
Agent + 金融的组合长期停留在两个坏形态：要么是「AI 荐股」信号服务（把判断外包给模型、无法审计），要么是一堆散装 prompt（每次运行顺序不同、风控步骤会被跳过）。高风险领域真正缺的不是更强的模型，而是一个能强制「先风控后选股」、且事后可复盘的流程骨架。

## 旧范式 vs 新范式
- **旧做法**：提示词库 / 提示词集市：「你是一个专业交易员，请分析……」——顺序不可保证、风控闸门可被模型自行绕过、产出物不留痕、无法做 postmortem。
- **新做法**：流程即产物（Process-as-Artifact）：用 YAML manifest 把「skill 调用顺序 + 决策闸门 + 留痕产物」编码成可版本化、可审阅、可被 Agent 机械执行的对象。Agent 的角色从「决策者」降级为「流程执行者」，人被强制留在闸门处做裁决。同时每个 workflow 显式声明 API profile（如 Alpaca 必需，手工 CSV 为 degraded fallback），把「能力降级」写进设计而非运行时报错。

## 生产力影响 (How)
这是「Agent 进入受监管/高风险领域」的通用解法雏形：把专业流程拆成 gate + artifact，让 Agent 只能推进流程、不能跳过闸门。可直接迁移到医疗分诊、合规审查、法律尽调、安全审计。开发者获得的不是「AI 炒股工具」，而是「如何让 Agent 在不能出错的流程里干活」的工程模板。

## 采用成本
时间：低-中。有文档站、`Your First Week` 上手路径、离线 quickstart；基础路径（15 分钟每日盘面体检）不需要付费数据 API。金钱：MIT 许可，免费；可选 Alpaca / FMP 数据源有成本。学习曲线：在于接受「AI 不替你决策」这一设定——有心智负担，但正是产品主张。

## 核心线索
- GitHub：https://github.com/tradermonty/claude-trading-skills
- 来源：https://github.com/trending/python?since=daily (703 stars today)
- 发布时间：2026-11-18
