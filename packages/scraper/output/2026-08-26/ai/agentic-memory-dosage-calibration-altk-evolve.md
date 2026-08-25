# Agentic Memory Dosage Calibration (ALTK-Evolve)

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次提出"记忆剂量需按模型校准"的三模式分类，引入 Guideline Set 区别于传统 replay |
| 采用广度 | ☆☆/5 | 学术阶段，开源 [agenttoolkit.github.io/altk-evolve](https://agenttoolkit.github.io/altk-evolve) |
| 时间新鲜 | ☆☆☆☆/5 | IBM Research 发布，HF Blog 2026-08-18 |
| 社区热度 | ☆☆☆/5 | HuggingFace 博客 + 多模型验证（8个模型） |
| **总体判断** | ✅ | **新范式（Agent 记忆工程新方向）** |

## 技术定义 (What)
ALTK-Evolve 是 IBM Research 提出的 Agent 记忆框架，核心发现：**Agent 记忆不是一个开关功能，而是需要按模型能力校准的"剂量"**。框架从 Agent 自身轨迹中蒸馏可复用的行为指南（guidelines），在推理时按需注入上下文。关键创新：根据模型能力分为三种模式——强模型（全量指南）、弱模型（精选检索）、饱和模型（无增益），并有针对性地选择注入策略。

## 行业痛点 (Why)
目前 Agent 记忆的默认假设是"越多越好"——堆更多上下文、更多历史。但实验证明这对弱模型适得其反（被淹没），对饱和模型毫无作用，只在正确剂量下才有效。gpt-oss-120b 用精选检索获得 +16.1pp 任务完成率提升，仅增加 5% tokens。这改变了"Agent 记忆 = 更多上下文"的粗糙认知。

## 旧范式 vs 新范式
- **旧做法**：Agent 记忆 = 堆上下文；记忆越多越好；全量 replay 所有历史轨迹
- **新做法**：记忆是模型特异的剂量；先判断模型模式 → 全量/精选/不注入；guideline 蒸馏而非原始轨迹 replay

## 生产力影响 (How)
- 弱模型通过精选检索获得最大收益（+16.1pp），成本仅增加 5%
- Prompt caching 使全量指南注入也可负担
- 无需训练、无需标注——纯推理侧优化
- 8 模型验证的可复用分类框架

## 采用成本
- **时间**：运行轨迹→蒸馏→部署，几小时级别
- **金钱**：仅推理 token 增量（+5%~50%）
- **学习曲线**：中等，需要理解三种模式判断

## 采用案例
- **gpt-oss-120b**：精选检索 +16.1pp TGC，+16.1pp SGC
- **DeepSeek-V3.2**：全量指南 +9.5pp TGC，+16.1pp SGC
- **Claude Opus 4.6 / GPT-5.5**：全量指南 +4.1~2.9pp

## 风险/局限
- 模式判断需要基准测试支持
- 目前仅在 AppWorld benchmark 上验证
- 饱和模型的根本原因尚未完全解释

## 核心线索
- 论文：[agenttoolkit.github.io/altk-evolve](https://agenttoolkit.github.io/altk-evolve)
- 首发来源：HuggingFace Blog / IBM Research, 2026-08-18
- 当前状态：研究阶段，开源