# Harness Adapters（harness 专用适配器）

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 把 harness 从"使用者的配置"变成"模型侧的适配器维度"。与已记录的 Harness-Model 配对律（评测侧）、Harness-Portable Plugin（插件侧）互补，此处补上模型侧 |
| 采用广度 | ☆☆/5 | HF 官方博客直接发布，具备一级分发能力；尚无第三方项目引用 |
| 时间新鲜 | ☆☆☆☆☆/5 | HF Blog 当期发布，2026-11 |
| 社区热度 | ☆☆/5 | 官方渠道背书，未观察到独立 HN 讨论 |
| **总体判断** | ✅ | **新范式** |

> 满足 3 项：概念创新 + 时间新鲜 + 一级分发渠道背书。

## 技术定义 (What)

为每个 agent harness（Claude Code、Codex、Cursor、OpenCode 等）单独训练一个轻量适配器，把该 harness 的 prompt 约定、工具调用语法、编辑风格烧进模型侧。模型不再是"一个权重"，而是"一组按 harness 索引的权重"。

## 行业痛点 (Why)

- 同一模型在不同 harness 下分数差异可达十个百分点级
- 使用者只能靠 prompt 微调或换 harness，无法从模型侧解决
- 模型厂商缺少下沉到 agent 框架的优化通道

## 旧范式 vs 新范式

- **旧做法**：一个通用模型 + 通用 system prompt，适配成本全压给使用者
- **新做法**：harness 成为适配器的一个索引维度，官方为每个主流 harness 交付专用权重

## 生产力影响 (How)

- **可预测性**：换 harness 的掉点变成"加载对应 adapter"而非重新调 prompt
- **成本结构变化**：专用 adapter 可用更小模型达到通用大模型在该 harness 下的效果
- **评测重构**：任何 agent 评测都必须声明 harness，否则数字不可比

## 采用成本

- 走官方路径：低，换权重即可
- 自建路径：中，需该 harness 的真实会话轨迹 + 一次 LoRA 级微调 + 逐 harness 基线评测

## 风险/局限

- **harness 碎片化**：每个 harness 一个大版本就可能要求新 adapter，维护成本随 harness 数量线性增长
- **生态锁定**：官方仅覆盖主流 harness，小众 harness 反而被固化在劣势位
- **验证缺口**：HF 正文抓取被工具限制阻断，以上基于标题与摘要语义判断；具体方法与数字需读原文核实

## 核心线索

- 出处：https://huggingface.co/blog/harness-adapters-at-scale
- 发布时间：2026-11（< 1 个月）
- 当前状态：活跃（官方发布）
