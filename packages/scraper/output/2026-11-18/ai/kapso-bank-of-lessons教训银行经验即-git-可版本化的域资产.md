# Kapso — Bank of Lessons（教训银行：经验即 git 可版本化的域资产）

## 技术定义 (What)
Kapso 是 Leeroo（YC P25）开源的「实验—部署—学习」引擎。核心创新是 **Bank of Lessons（教训银行）**：每条 lesson 由「正文 + 边界（boundary，说明在什么条件下适用）+ 置信度分数（credence score）+ 证据（evidence）」四元组构成，由历次实验轨迹归纳或演绎而来，存放在 **git 仓库**里（`kapso experience share/list/update`），可像代码库一样共享、列出、更新与 A/B 测试。系统给定目标与成功标准后，自动跑一棵实验树（假说→实现→验证），`learn()` 把结果归因到具体假说与实现，并**用重建/不重建两版对照**来度量银行更新是否真的更好；`deploy()` 再用一轮更短的同类实验把最优解适配到目标栈（Docker/Modal/BentoCloud/LangGraph）。关键约束：验证器（verifier）带指纹，任何实验都无法访问或篡改；实验模块只能「提议」修改评估指标/标准，由 verifier 批准或驳回。

## 行业痛点 (Why)
企业数据/ML 场景的知识是「迭代出来」的（调查→假说→实验→改进），但现有做法要么把它塞进模型权重（重训 tabular 基座模型，慢且不透明），要么用 RAG 检索文档（没有在具体环境里被验证过，价值极低）。换个环境就得从零开始，经验无法复用、无法审计、无法版本化。

## 旧范式 vs 新范式
- **旧做法**：把领域学习固化在模型权重里（重训/微调基座模型）；用 RAG 检索通用文档来「喂知识」；靠顾问开几个月的会、或先做一版业务本体（ontology）再去套数据。
- **新做法**：把领域学习固化在**可版本化的教训银行 + 域 harness** 里，模型与 coding agent 均无关。经验是 git 上的资产，可共享、可 A/B、可追溯证据；评估标准本身也可被提议修订，但必须由隔离的 verifier 批准。

## 生产力影响 (How)
领域能力的复利不再依赖 GPU 重训成本——README 明确称「更新一个教训银行的开销远低于重训一个表格基座模型」。实测战绩：Stanford RelBench 三榜全第一（分类 81.2 AUROC vs KumoRFM-v2 79.3 / 回归 0.2476 NMAE / 推荐 18.4 MAP vs 9.3）；MLE-bench 开源系统第一；ALE-Bench 终评 1909 Elo（vs ALE Agent 1879）；IOAI² 2026 以 536.07 分超过全部 471 名人类选手并拿下 Grand Master Trophy（AI 系统前三）。配套 Leeroopedia 公开银行约 10 万页、月 600 万请求、其中约 28% 来自 AI agent。对企业的意义：agent 做数据/ML 工程时，第一次有了「组织记忆」而非「每次重新猜」。

## 采用成本
`pip install leeroo-kapso`（Python 3.10+），但硬性前置是 Node 18+ 且同时登录 **Codex CLI + Claude Code CLI**（无直接 API fallback），所以推理成本实际走自己的订阅额度。可选 Docker 起 Weaviate+Neo4j（本地语义检索/知识图谱索引）。Leeroopedia 密钥可选（新账号 $20 额度）。现成 harness 只有「预测建模」和「竞赛编程」两个，自有领域需用 `/kapso:harness` 自己写。

## 核心线索
- GitHub：https://github.com/Leeroo-AI/kapso
- 来源：https://news.ycombinator.com/item?id=50471281
- 发布时间：2026-11-18
