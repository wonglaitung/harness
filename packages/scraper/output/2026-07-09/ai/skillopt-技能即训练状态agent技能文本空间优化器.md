# SkillOpt：技能即训练状态 — Agent技能文本空间优化器

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首创"将技能文档视为冻结Agent的可训练状态"，用深度学习优化器的纪律训练自然语言技能 |
| 采用广度 | ☆☆☆☆/5 | gbrain、gbrain-evals、darwin-skill已集成；支持Claude Code/Codex/Copilot/Devin/OpenClaw五大后端 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年6月v0.1发布，7月v0.2发布SkillOpt-Sleep |
| 社区热度 | ☆☆☆☆/5 | GitHub日增261星，微软研究院+arXiv论文背书 |
| **总体判断** | ✅ | **新范式 — Agent技能从手工艺到工程化训练** |

## 技术定义 (What)
SkillOpt是一种文本空间优化器，将Agent的技能文档（skill.md）视为"冻结模型的可训练参数"，用类似训练神经网络的纪律（epoch、batch size、学习率、验证门控）来优化自然语言技能。优化后的产物是一个紧凑的`best_skill.md`（300-2000 tokens），部署时零额外推理调用。

## 行业痛点 (Why)
当前Agent技能的三大困境：
1. **手工艺式**：人工编写prompt/skill，质量参差不齐
2. **一次性生成**：强模型一次性生成，无法可靠改进
3. **松散自修订**：自我修订缺乏纪律，经常越改越差

没有一个方法像深度学习优化器那样，能可靠地在反馈信号下持续改进技能。

## 旧范式 vs 新范式
- **旧做法**：人工编写skill → 一次性LLM生成 → 松散自修订（无验证门控，无收敛保证）
- **新做法**：将skill.md视为可训练状态 → rollout评分 → 反思聚合 → 有界编辑(add/delete/replace) → 验证门控（仅当held-out分数严格提升时接受） → 部署best_skill.md

## 生产力影响 (How)
- **GPT-5.5上**：直接聊天+23.5分，Codex agentic loop +24.8分，Claude Code +19.1分
- **跨模型迁移**：优化后的skill可跨模型规模、跨执行框架迁移，无需重新优化
- **SkillOpt-Sleep**：夜间离线自进化引擎（harvest → mine → replay → consolidate），Agent睡觉时技能自动进化
- **零推理开销**：部署产物是纯文本skill，不增加任何模型调用

## 采用成本
- **时间**：pip install skillopt，配置后端API即可开始训练
- **金钱**：训练过程需要调用LLM API（rollout+优化），但部署零成本
- **学习曲线**：需理解epoch/batch/lr等训练概念在文本空间的映射，有WebUI监控面板辅助

## 采用案例
- **gbrain**：集成SkillOpt进行技能优化，已发布eval基准
- **darwin-skill**：基于SkillOpt的技能进化框架
- **Codex CLI / Claude Code CLI**：作为执行框架直接支持，6个benchmark上52个评估单元全部最优或并列最优

## 风险/局限
- 训练质量依赖rollout评分的准确性，评分偏差会传播到优化结果
- 文本学习率和编辑预算需要手动调参
- 当前仅支持单技能文档优化，多技能协同优化尚未覆盖
- SkillOpt-Sleep仍为preview阶段

## 核心线索
- GitHub：https://github.com/microsoft/SkillOpt
- 论文：https://arxiv.org/abs/2605.23904
- 项目页：https://microsoft.github.io/SkillOpt/
- 首发时间：2026-06-02（v0.1.0 PyPI发布）
- 当前状态：活跃（v0.2.0已发布，SkillOpt-Sleep preview）