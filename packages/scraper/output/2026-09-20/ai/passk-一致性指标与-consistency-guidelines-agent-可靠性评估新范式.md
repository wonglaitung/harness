# ALTK-Evolve Consistency — Pass^k 一致性指标与一致性指南

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆ | 明确提出 Pass^k 指标（区别于 Pass@k）、"consistency gap"、"flip-prone 决策点"等全新概念，并给出诊断+修复闭环 |
| 采用广度 | ☆☆ | IBM Research，开源 altk-evolve，早期 |
| 时间新鲜 | ☆☆☆☆☆ | 2026-09-15 发布，arXiv:2609.08832 |
| 社区热度 | ☆☆ | Hugging Face 官方博客 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)
提出 **Pass^k** 指标：衡量 Agent 在 k 次重复运行中**每次都成功**的任务占比（是 Pass@k 的悲观镜像）。发现"一致性缺口（consistency gap）"= Mean@k − Pass^k。用 **Consistency Analyzer** 重采样 Agent 轨迹，定位**易翻转（flip-prone）决策点**，再生成**一致性指南（consistency guidelines）**注入推理，将缺口减半。

## 行业痛点 (Why)
现有 Agent 基准只报平均成功率（Mean@k），隐藏了可靠性问题：一个 Agent 平均 77.4% 成功，但对同一任务"每次都能成功"的比例只有 53%——24.4 点的一致性缺口。生产环境要的是"重问同样问题是否仍然可靠"。

## 旧范式 vs 新范式
- **旧做法**：基准只报 Mean@k（平均 pass rate），用更大模型解决"能力"问题
- **新做法**：用 Pass^k 量化一致性，诊断易翻转决策点，用一致性指南针对"稳定性"这个正交轴

## 生产力影响 (How)
- 一致性缺口从 24.4pp 降至 12.0pp（Pass^5 53%→69%），不损失平均精度
- 中/难任务收益最大（+22.9pp / +14.3pp）
- 检测完全黑盒（无需 logits/内部状态），一次轨迹即可诊断

## 采用成本
低：开源 altk-evolve 库，一个新指标 + 诊断工具 + 指南生成管道

## 采用案例
- AppWorld（168 任务）上 ReAct + GPT-4.1 的可靠性提升
- 金融对账、合同核查等 mission-critical Agent 工作流

## 风险/局限
- 评估/改进依赖额外模型调用（每决策点一次离线调用）
- 指南生成质量依赖上游模型

## 核心线索
- GitHub：https://github.com/AgentToolkit/altk-evolve
- 首发来源：https://huggingface.co/blog/ibm-research/altk-evolve-consistency
- 发布时间：2026-09-15
- 当前状态：试验中（arXiv:2609.08832）