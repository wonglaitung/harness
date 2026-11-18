# StarSling — Agent-Native CI：会自我优化的 CI，以及「评审不可自改」机制

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 「Agent-native CI」被明确定义为一个类别：CI 会随使用时长自我变快。配套的 Reviewer Integrity 机制（技能只从 trusted base branch 加载，PR 不得改写自己的评审器）是解决 agent 评审可信问题的干净工程答案 |
| 采用广度 | ☆☆☆/5 | 3M+ CI job 跑过；Mastra / Better Auth / Partcl 三家公开案例；YC P25 |
| 时间新鲜 | ☆☆☆☆☆/5 | Launch HN 2026-11，Adaptive Compute 为最新发布 |
| 社区热度 | ⚠️☆☆/5 | Launch HN 仅 58 points，远低于 AI 类项目的 100+ 门槛；靠公开 benchmark 与客户数据而非 HN 讨论支撑 |
| **总体判断** | ✅ | **新范式**（概念创新 + 采用广度 + 时间新鲜，3/4 满足；社区热度偏弱需持续观察） |

## 技术定义 (What)

两个产品面 + 一套 skills：

**1. Runners（硬件层）**
- 5th Gen AMD EPYC，drop-in 替换 `ubuntu-latest` / `ubuntu-24.04`
- **Adaptive Compute = Sandbox Router + Afterburner**
  - Sandbox Router：每个 job 路由到当前最快可用的 sandbox
  - Afterburner：运行中的 step 可动态 +25% CPU / +50% RAM，不额外计费
  - 合计宣称比 GitHub 托管 runner 快至 2.32×
- **StarSling Disks**：持久化目录挂载进 runner，依赖已就绪。Mastra 4.5GiB pnpm store 约 25s 就绪，比 `actions/cache` 快 4.5×；同仓库 PR 可读默认分支已发布的 disk

**2. Review Runners（评审层）**
- 一个 workflow 文件即可让每个 PR 被当作 GitHub Actions job 分析
- 用你自己的 model key、你代码库里的 review skills / scripts、团队定义的 reviewer
- **关键机制**：skills 与 instructions 从受信任的 base branch 加载 → PR 无法重写自己的 reviewer
- 输出是 PR 上的评审评论，且发生在人类打开 PR 之前

**3. Agent Skills（开源，本地跑）**
- `/ci-speedup`：读你的 workflows，把证据交给 coding agent 去修 wall clock
- `/ci-score`：评估 GitHub Actions 配置质量
- `/ci-secure`：关闭关键攻击面
- `/sling`：诊断失败的 job

## 行业痛点 (Why)

StarSling 的定位一句话说透了：「Agents write code faster than CI can check it.」（Agent 写代码快过 CI 能检查的速度。）

这带来三重挤压：
1. **数量**：agent 让 PR 数量暴涨，排队时间成为主导延迟
2. **成本**：每个 PR 都跑全量 CI，账单线性膨胀
3. **信任**：agent 也写评审 agent，但没人能保证评审规则没被被测代码污染

传统 CI 只能解第一层（买更快机器），对第二、三层无解。

## 旧范式 vs 新范式

| | 旧 | 新 |
|---|---|---|
| CI 优化 | 人工读 log、一次性重构、随后腐化 | agent 持续读 job/log/遥测，主动开 PR 优化 |
| 换硬件 | 迁移工程 | 改一行 `runs-on` |
| 缓存 | `actions/cache`，冷启动每次重下 | 持久化 Disk，依赖预先就绪 |
| 突发负载 | 静态规格，选小了慢、选大了贵 | Afterburner 运行时加核，不加钱 |
| Agent 评审 | SaaS 黑盒，指令来源未知 | 跑在你自己的 CI 里，指令锚定 base branch |

## 生产力影响 (How)

三个公开案例的数字足够具体，且有一个是「自证」：

- **Mastra**：6× 快（29m56s → 5m06s wall p95）。其引言点出本质：「在 Mastra 我们跑得太快，瓶颈变成评审和 CI。时间成本会复利。」
- **Better Auth**：E2E 2×（2m22s → 1m04s）。
- **Partcl**：队列时间 16×（9.5min → 35s）。且「迁移到 StarSling Runners 一天之内，他们的 agent 开了一个 PR，让我们的 Rust CI 测试真的快了 2×」。

对 agent-heavy 团队，这是把「验证吞吐」从组织瓶颈变成可扩容资源。

## 采用成本

- **迁移**：一行 YAML。所有 job / action / build command 保持不变。
- **金钱**：$0.008/min（4vCPU/16GB，比 GitHub 便宜 33%），按秒计费、无 1 分钟下限、排队不计费，首月 2000 免费分钟。GPU：RTX 4090 $0.02522/min、RTX 5090 $0.03022、RTX PRO 6000 $0.06422，H100 待上线。Disk 存储 $0.50/GB-month。
- **技能门槛**：无需重写工作流；若要开 Review Runners 需一个 model key。
- **风险敞口**：把 CI 交给第三方 runner 意味着构建环境信任边界外移，需评估合规要求。

## 采用案例

- **Mastra**（TypeScript 框架）：6× 测试套件提速 + agent 持续提交优化 PR。
- **Better Auth**（认证库）：E2E 2× 提速，作者称「省下无数小时，靠他们的 agent 优化我们的 CI」。
- **Partcl**（Rust 项目）：队列 16× 缩短 + agent 开 PR 令 Rust 测试再快 2×。

## 风险 / 局限

- **社区信号偏弱**：Launch HN 仅 58 分，尚未形成独立开发者讨论密度。案例均来自早期客户，存在选择偏差。
- **benchmark 自建**：public benchmark 仓库（`starsling-demo-org`）由 StarSling 自己维护。
- **第三方 runner 的信任成本**：CI 里跑的是你的代码、你的 secrets。迁移前需确认隔离与审计能力（Afterburner 动态加核也意味着运行时资源不固定，对需要确定性性能的环境不友好）。
- **「自我改进」的边界未验证**：agent 开的优化 PR 需要人类 merge，长期是否会产生「为刷指标而优化」的漂移，尚无长期数据。
- **Windows/非 Ubuntu 覆盖有限**：核心价值集中在 Linux/Ubuntu 工作流。

## 核心线索

- 产品站：https://starsling.dev/
- Adaptive Compute 发布文：https://starsling.dev/blog/adaptive-compute
- Agent Skills：https://starsling.dev/skills
- 公开 benchmark 仓库：https://github.com/starsling-demo-org
- HN Launch：https://news.ycombinator.com/item?id=starsling（58 points，YC P25）
- 发布时间：2026-11（Adaptive Compute 为最新）
- 当前状态：**活跃（商业化早期）**
