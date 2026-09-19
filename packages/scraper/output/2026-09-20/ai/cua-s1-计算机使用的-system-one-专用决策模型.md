# CUA-S1 — System One Model for Computer Use

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆ | 引入"System One Model"类别——工程类比"快速、有界决策"，非自回归逐 token 生成 |
| 采用广度 | ☆☆☆ | 开源家族 + Hugging Face 权重，HN 有独立讨论"non-autoregressive decision models with RL"1052 分 |
| 时间新鲜 | ☆☆☆☆ | Show HN 2026年，source-only 早期研究发布 |
| 社区热度 | ☆☆☆ | Show HN 56 分；HN 相关讨论 1052 分 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)
CUA-S1 是一族小型专用 **System 1 模型**，用于计算机使用（computer use）。"System 1"是工程类比：指**快速、有界决策**（如选择字段该填哪个值、是否离开某元素），而非通用 Agent 的规划与推理。首个研究聚焦表单场景：从结构化界面元素和文档值**打分决策**，而非逐 token 生成响应。

## 行业痛点 (Why)
通用 LLM Agent 做计算机操作时，把"该点哪里/填什么"这类**有界决策**当作生成任务，用大模型逐 token 输出，慢且浪费。这类决策其实只需要一个**快速、有界、可判定**的小模型。

## 旧范式 vs 新范式
- **旧做法**：通用大模型逐 token 生成 GUI 操作序列（System 2 式推理驱动每一个点击）
- **新做法**：小型专用打分模型对结构化界面元素做有界决策（选择值/是否离开），应用代码编排动作顺序

## 生产力影响 (How)
- 小模型（远小于通用模型）承担有界决策，显著降低延迟与成本
- 提供合成数据生成、训练、评估全链路，配合 Cua Driver 在 macOS/Windows/Linux 执行

## 采用成本
中等：Python 模型代码 + 合成数据 + 训练，需自行训练/微调权重（权重在 HF 托管）

## 采用案例
- 表单自动填写（首个研究场景）
- 桌面自动化决策（配合 Cua Fleets/Driver/Bench）

## 风险/局限
- 早期 source-only 研究发布，非生产就绪
- System 1 是工程类比，非严格架构分类，不替代通用 Agent 规划

## 核心线索
- GitHub：https://github.com/trycua/cua
- 首发来源：https://github.com/trycua/cua (Show HN)
- 发布时间：2026年
- 当前状态：试验中（早期研究发布）