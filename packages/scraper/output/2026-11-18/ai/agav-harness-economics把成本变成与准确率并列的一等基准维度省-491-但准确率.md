# Agav — Harness Efficiency Economics

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 明确提出「AI 编码成本常常是 harness 问题，不只是模型问题」，并在固定模型+固定费率下做成本对照，发布中位 trial 成本、总支出差、任务级遥测与局限；主动把成本结论与准确率结论切开 |
| 采用广度 | ☆☆/5 | SWE-bench-Live Lite #1-verified（62.0%，186/300，有公开提交）；Terminal-Bench 2.1 84.7%（PR 仍在 review）——有第三方榜单背书，但生态集成尚少 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026-11 Show HN 新发布，自标 Experimental Beta |
| 社区热度 | ☆☆/5 | Show HN 仅 26 points（刻意定位「少烧 token」的小众工具）；r/agav、Discord、X 生态齐备但规模小 |
| **总体判断** | ⚠️ | **观察中**：概念创新 + 时间新鲜成立；采用广度与社区热度尚未达标 |

## 技术定义 (What)
Agav 是一个终端原生编码 Agent（Apache-2.0，自包含二进制，不需要 Node.js）。技术上它做的是 harness 层的浪费消除：复用缓存上下文、限制重复工作、中断无产出的修补循环、给重试和预算设上界、把子 Agent 探索隔离在独立上下文而不是反复重发同一份仓库。

关键不在于功能表，而在于它公布的是什么：在 Terminal-Bench 2.1 上固定 GPT-5.6 Luna 与同一费率，89 个任务的中位估计 trial 成本 15.2¢、总支出比 Codex 低 49.1%；同一比较中它通过 60.4%、Codex 通过 76.6%。原文一句话把自己钉住：「这是成本结果，不是更高准确率的主张。」

## 行业痛点 (Why)
同一份仓库上下文被每个 turn 重发、失败的修补循环持续空转、重试没有预算、子 Agent 探索把主上下文撑爆——这些浪费都发生在 harness 层，与模型无关。但排行榜只排 pass rate，于是 harness 的成本效率既不可见也无法被竞争，选型讨论退化成品味与品牌之争。

## 旧范式 vs 新范式
- **旧做法**：榜单唯一轴是准确率；成本作为「你选了哪家模型」的副作用被忽略；厂商把成本与能力混在一个叙事里讲。
- **新做法**：把 harness 当被测量对象。固定模型与费率做成本对照，公开方法论/遥测/任务级数据/局限，并**显式承认自己在准确率上落后**，让读者得到可比较的权衡曲线而非结论式宣传。

## 生产力影响 (How)
- 对采用团队：拿到的是「省一半钱、少 16 个点通过率」这种可验算的权衡，而不是「更强/更便宜」的口号，能按任务价值密度分流（高频低难任务用低成本 harness，关键改写用高准确率 harness）。
- 对 harness 开发者：缓存复用、重试预算、上下文隔离、空转中断从「优化技巧」升级为可发布、可复现的对外指标。
- 对 CI 场景：`agav run` / `--print` 支持非交互运行与 JSON Schema 输出，可直接嵌入流水线。

## 采用成本
- 安装：`curl -fsSL https://agav.dev/install.sh | bash` 一条命令，单文件二进制；Windows 有 ps1/cmd 两种。
- 起步零成本：OpenRouter / NVIDIA NIM 免费日额度；也可接 OpenAI / Anthropic / Gemini / Vertex / Ollama，会话中 `/model` 随时切换。
- 风险成本：Experimental Beta，官方明示会有 breaking change 与粗糙边缘。

## 采用案例
- **SWE-bench-Live Lite**：#1-verified，62.0%（186/300），有公开提交可查。
- **Terminal-Bench 2.1**：84.7%（377/445 trials ±0.84%），提交 PR 仍在 review——即「尚未完全确证」。
- **成本研究**：《The economics of coding with Agav》公开方法论、遥测、实现参考与局限。

## 风险/局限
- **准确率确有差距**：同条件 60.4% vs Codex 76.6%，省钱的代价是能力，不能当作「更好的编码 Agent」使用。
- **榜单状态不完整**：Terminal-Bench 提交仍处 review，84.7% 应视为待确认。
- **基准范围**：成本研究仅 89 个任务、单一模型费率，外推需谨慎（作者自己也这么写）。
- **Beta 状态**：接口与行为可能随时变化，不宜直接用于关键生产路径。

## 核心线索
- GitHub：https://github.com/prapaa-ai/agav
- 文档：https://docs.agav.dev
- 成本研究：https://agav.dev/research/cost-efficiency
- 首发来源：Show HN（26 points，2026-11）
- 发布时间：2026-11
- 当前状态：活跃，Experimental Beta
