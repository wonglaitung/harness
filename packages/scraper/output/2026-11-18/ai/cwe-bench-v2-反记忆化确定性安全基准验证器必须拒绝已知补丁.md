# CWE-bench v2 — 反记忆化确定性安全基准

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 把「反记忆化」提升为**基准任务准入条件**（验证器必须让已知上游补丁失败），并让基准成为可直接从数据集仓库执行的任务包（Harbor + registry.json） |
| 采用广度 | ☆☆/5 | 已有 11 个前沿模型被评测（Gemini 4 Argon、Claude Opus 5.5、DeepSeek V4.1 Flash 等），结果以 PR 方式进 HF 数据集页 leaderboard；范式本身尚待其他基准跟进 |
| 时间新鲜 | ☆☆☆☆☆/5 | v2 于 2026-11-03 发布 |
| 社区热度 | ☆☆/5 | HF 官方博客 + 公开 leaderboard，暂无 HN/GitHub 大范围讨论 |
| **总体判断** | ✅ | **新范式（评测方法论层：抗污染验证器 + 基准即任务包）** |

## 技术定义 (What)
CWE-bench v2 是 Collinear AI 推出的前沿安全能力基准，公开 100 个任务、覆盖 **91 类 CWE**，另维护 held-out 集。每个任务是自包含的 **Harbor task**：一个 Docker 化环境 + 一条读起来像真实工作指令（而非评测设定）的 prompt + 一个**确定性程序化验证器**。数据集自带 `registry.json`，因此可一条命令从 HF 仓库直接跑完整基准。评分全程序化、可无额外成本复现；程序化检查经 LLM 裁判小组打磨以偏向"更难更公平"。

## 行业痛点 (Why)
安全基准最容易被两件事毁掉：**污染/记忆化**（模型见过 CVE 的上游补丁，"答对"只是背答案）与**验证器错位**（检查某种修复的代码结构，而非漏洞是否真被修好）。而安全场景是不对称的：防御方必须每次都对，攻击方只需成功一次，因此"分数涨了但能力没涨"的代价极高。同时旧基准复现成本高，无法形成可比较的性价比结论。

## 旧范式 vs 新范式
- **旧做法**：静态题面 + 参考答案/模糊裁判；环境私有、复现靠自建脚本；公开补丁即标准答案，污染无法排除。
- **新做法**：可执行任务包（Docker + 指令 + 确定性验证器）+ registry.json，一条命令端到端复现；任务准入强制六问，其中关键两条——验证器必须检查"正确行为"而非某一种修复结构；**验证器必须让已记忆的已知上游补丁失败**；公开集与 held-out 集分离。

## 生产力影响 (How)
- 安全 Agent 团队：得到一个抗污染、可复现、成本可比的靶场，能直接做 **pass@1 vs 每次 rollout 成本** 的 Pareto 选型（DeepSeek V4.1 Flash 57.0% pass@1 @ $0.04；Claude Opus 5.5 +10pt @ $1.83；Gemini 4 Argon 67.8% @ $3.92）。
- 研究侧：天花板清晰可量化——最优模型仍**每次都失败 19% 的题**；95/100 题至少被一个模型解出，证明任务可解、长尾未解。
- 工程侧：`-k 4` 取 400 次试验平均奖励，天然抑制单次采样噪声。

## 采用成本
- 运行：Docker + Harbor；数据集需在页面接受访问条件，HF token 存入 git credential helper；一条 `harbor run --repo ... -d cwe-bench@2.0 -k 4` 即可。
- 贡献：开 PR 提交 results 文件（HF 数据集页 leaderboard）或向 leaderboard Space 提 PR；新增任务需满足六项质量门禁。

## 风险/局限
- 100 题规模对细粒度能力区分有限；91 类 CWE 覆盖广但每类样本稀疏。
- held-out 集不对公众开放，外部无法独立验证其难度分布。
- 「反记忆化」只能验证模型对**已公开**补丁不生效，对未公开但风格相似的记忆仍无解。

## 核心线索
- 博客：https://huggingface.co/blog/cwe-bench （2026-11-03）
- 公开数据集/任务：https://huggingface.co/datasets/collinear-ai/cwe-bench
- Leaderboard Space：https://huggingface.co/spaces/collinear-ai/cwe-bench-leaderboard
- 官方站：https://cwe-bench.com/
- 当前状态：公开集 + leaderboard 已上线，活跃维护
