# SkillEvaluator

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首次把「Skill 的边际贡献」定义为可对照测量的量（with/without 双组实验），并给出分层质检模型（Tier 1 确定性 → 模型评分 rubric）。评测粒度从「模型/harness」下沉到「能力单元」，这是新的评测坐标系。 |
| 采用广度 | ☆☆☆☆/5 | 官方锚定为 NVIDIA Verified Skills pipeline 的一环，与 NVIDIA/skills（Agent Skills for NVIDIA products）互为上下游；符合 agentskills.io 规范；同时以 Agent Skill 形态自举分发，可被 Claude Code、Codex 等任意 skill-aware agent 消费。CI 双平台（GitHub/GitLab）覆盖。 |
| 时间新鲜 | ☆☆☆☆/5 | 配套论文 arXiv 2608.20614（2026-08），发布于约 3 个月前，< 6 个月阈值。 |
| 社区热度 | ☆☆☆/5 | 已有 PyPI 正式包 + docs.nvidia.com 官方文档站 + NVIDIA Developer Blog + 官方 livestream（"Ask the Experts: Evaluating Agent Skills"），企业背书强；但独立第三方引用/讨论尚未形成热度。 |
| **总体判断** | ✅ | **新范式（高置信度）** |

## 技术定义 (What)
SkillEvaluator 是 Agent Skill 的评测器。Skill = 按 [Agent Skills 规范](https://agentskills.io/) 组织的指令与支撑文件目录。SkillEvaluator 做两件事：**先质检**（分层 Tier 检查，Tier 1 为确定性检查，无需 LLM），**再对照**（对比「使用该 skill」与「不使用该 skill」两次运行，量化技能对任务结果的真实影响）。三条接入路径共用同一 CLI：本地 `skillevaluator validate ./my-skill --tiers 1`、CI（`skillevaluator ci init` 自动开 setup PR）、Agent 内（`npx skills add NVIDIA/SkillEvaluator`，然后直接问「Is my skill any good?」）。

## 行业痛点 (Why)
2026 年 Agent Skill 已成为能力分发的事实标准，但生态里没有质量门槛。任何 skill 只要写几段 prompt 就能被安装，而传统软件工程手段对它失效——它不是代码，单测和类型检查无法验证「这段自然语言指令是否真的让 Agent 做得更好」。结果是 skill 生态趋向 prompt 集市：靠 Star 数和作者自述背书，劣质 skill 白占上下文，恶意 skill 污染 Agent 行为。缺少边际贡献度量，也无法回答「这个 skill 到底值不值得装」。

## 旧范式 vs 新范式
- **旧做法**：Skill 质量靠作者自述 + Star 数 + 人工试用；评测粒度停在「整个模型/harness 的能力」，无法分离单个 skill 的贡献；CI 对 prompt/instruction 类资产零检测。
- **新做法**：Skill 进入 CI 成为回归资产。Tier 1 确定性质检 → 高层 rubric/模型评分 → with/without 对照实验量化边际收益 → PR 级质量门禁 → NVIDIA Verified Skills 认证流水线。

## 生产力影响 (How)
让 skill 从「不可控的 prompt 文本」变成可回归、可阻断、可认证的工程资产。团队能在 PR 阶段发现某个 skill 拖低任务成功率，避免劣质技能进入内部 Agent 库；Skill marketplace/registry 由此获得建立信任评级的基础设施；Skill 作者第一次能回答「我的 skill 真的有效吗」。这是 Skill 生态从「数量扩张」转向「质量筛选」的关键一环。

## 采用成本
- **Tier 1**：零成本。`pip install skillevaluator`，无需 API Key，分钟级跑完确定性检查。
- **Tier 2+（模型评分）**：需 NVIDIA Build API Key 或自托管 NIM，成本随评测样本量线性增加。
- **CI 接入**：`skillevaluator ci init` 半自动（GitHub 开 setup PR；GitLab 需复制模板）。
- **真实成本**：为每个 skill 构建可复现任务集与判定标准——这是评测的固有难题，工具无法代劳。

## 采用案例
- **NVIDIA Verified Skills pipeline**：SkillEvaluator 作为质量门禁环节，与 [NVIDIA/skills](https://github.com/NVIDIA/skills)（Physical AI / robotics / CUDA / RAG 等 Agent Skills 集合）配套使用，形成「产出 skill → 评测认证 → 分发」的闭环。
- **Skill 自举**：以 skill 形态分发自身，Agent 可直接被询问「我的 skill 好不好」，把评测入口下推到自然语言交互层。

## 风险/局限
- **ground truth 依赖**：对照实验的有效性取决于任务集与判定标准的质量，评测设计不当会产生虚假信心。
- **模型耦合**：Tier 2+ 默认绑定 NVIDIA NIM 生态（nemotron 系列），跨模型可迁移性需自行验证。
- **短期收益不显**：对单人自用的小规模 skill 集合，建立任务集的成本可能高于收益；价值主要在多 skill 协作与组织级分发场景释放。
- **生态尚早**：第三方采用证据仍少，能否成为跨厂商通用标准取决于 agentskills.io 规范本身的采纳广度。

## 核心线索
- GitHub：https://github.com/NVIDIA/SkillEvaluator
- PyPI：https://pypi.org/project/skillevaluator/
- 论文：arXiv 2608.20614
- 官方文档：https://docs.nvidia.com/skills/skillevaluator/
- 上游规范：https://agentskills.io/
- 发布时间：2026-08（论文）；当前状态：活跃，企业维护，暂未开放外部贡献