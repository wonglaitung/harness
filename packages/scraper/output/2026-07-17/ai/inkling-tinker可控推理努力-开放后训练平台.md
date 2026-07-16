# Inkling + Tinker：可控推理努力 + 开放后训练平台

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | "Controllable Thinking Effort"可控推理努力——同一模型通过effort参数0.2-0.99连续调节推理深度，而非切换不同模型；Tinker后训练SDK将微调民主化 |
| 采用广度 | ☆☆☆/5 | HN 1176分极高关注；Inkling Playground开放试用；Tinker平台已上线；但生态尚在早期 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年7月16日发布，极新 |
| 社区热度 | ☆☆☆☆☆/5 | HN 1176分，为当日最高分帖子之一 |
| **总体判断** | ✅ | **新范式 — 可控推理努力+开放后训练民主化** |

## 技术定义 (What)
Inkling是Thinking Machines Lab发布的975B总参数/41B激活的MoE开放权重模型，核心创新是**可控推理努力（Controllable Thinking Effort）**：开发者可通过effort参数（0.2-0.99）连续调节模型的推理深度和token消耗，而非在多个不同规模模型间切换。配套Tinker平台提供API化的后训练SDK，支持SFT、RLHF、DPO、蒸馏、多Agent RL等全流程微调。

## 行业痛点 (Why)
当前LLM推理存在"要么全量推理要么换小模型"的二元困境：高effort任务需要强模型但成本高，低effort任务用强模型浪费token、用弱模型质量差。开发者无法在同一模型上按需调节推理深度。同时，后训练（post-training）技术门槛高，普通开发者难以自行完成RLHF/DPO等微调流程。

## 旧范式 vs 新范式
- **旧做法**：为不同effort需求部署不同规模模型（GPT-4 vs GPT-4-mini），或固定推理深度无法按需调节；后训练需要自建GPU集群和训练管线
- **新做法**：单一模型通过effort参数连续调节推理深度，在Terminal Bench 2.1上以1/3 token达到Nemotron 3 Ultra同等性能；Tinker API化后训练让微调像调用API一样简单

## 生产力影响 (How)
1. **成本效率革命**：同一模型覆盖从快速响应到深度推理全场景，减少模型部署和维护成本
2. **后训练民主化**：Tinker SDK让非ML专家也能进行SFT/RLHF/DPO微调，降低定制化门槛
3. **迭代加速**：低effort快速验证+高effort精调，开发循环更快
4. **Inkling自微调**：模型可编写自己的微调任务并执行，展示自我改进闭环

## 采用成本
- 模型权重免费开放（HuggingFace）
- Tinker平台需注册API key，训练按计算量计费
- 本地推理需足够GPU资源（41B激活参数）
- 学习曲线：Tinker SDK有20+渐进式教程，入门门槛中等

## 采用案例
- **Inkling自微调**：Inkling使用Tinker编写并执行自己的微调任务，验证自我改进闭环
- **Design Arena**：在盲评Agentic Web Dev排行榜中位列开放权重模型前列
- **多轮精调游戏**：40轮GPT Codex评审反馈下持续改进多人Snake游戏

## 风险/局限
- 综合性能仍落后Claude Fable 5和GPT 5.6 Sol等闭源前沿模型
- 可控推理努力的effort参数调优需要经验积累
- Tinker平台依赖Thinking Machines Lab的云端训练服务，非完全本地化
- 生态尚在早期，社区工具和集成有限

## 核心线索
- 官网：https://thinkingmachines.ai/
- Tinker平台：https://tinker-console.thinkingmachines.ai
- Tinker Cookbook GitHub：https://github.com/thinking-machines-lab/tinker-cookbook
- 首发来源：https://thinkingmachines.ai/news/introducing-inkling/
- 发布时间：2026年7月16日
- 当前状态：活跃 / 早期