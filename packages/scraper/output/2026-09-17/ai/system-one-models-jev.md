# System One Models / Jev — 类型安全结构化决策的新模型类别

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 全新模型类别（System One），RLCD 训练法、并行采样、仅输出结构化概率值，从根本上区别于 LLM |
| 采用广度 | ☆☆/5 | 刚发布（early access），生态待建 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026-09-16 首发 |
| 社区热度 | ☆☆☆☆☆/5 | HN 1784 分（榜首），极高的关注度 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)
由 TypeSafe AI（前 OpenAI 团队）发布的新模型类别。放弃字符串生成，输入非结构化程序状态，以并行采样一次性输出类型安全的结构化决策（含校准概率与置信度），数学上不可能产生类型错误或幻觉。

## 行业痛点 (Why)
LLM 聊天能力超前，但自动化落地受阻：输出需解析、可能幻觉、延迟 3-329 秒、输出 token 昂贵、置信度校准差——自由度带来的"失控风险"使其难以可靠嵌入软件。

## 旧范式 vs 新范式
- **旧做法**：RLHF/RLVR 训练的 LLM，自回归逐 token 生成字符串，下游代码解析+校验，有幻觉与不一致风险。
- **新做法**：RLCD 训练，并行采样一步出结果，类型安全结构化值 + 校准概率，70-500ms 端到端，输出免费。

## 生产力影响 (How)
40x-200x 更快、444x 更便宜，解锁实时应用、PB 级 map-reduce、LLM 守卫/评分/越狱检测等此前不可行的自动化场景。

## 采用成本
需学习新 API 范式、放弃字符串思维；early access 阶段，生态小。

## 采用案例
- TypeSafe 自家工作流评测（workflow evals）：相比 GPT-6 Astra / Fable 参考值，"own the Pareto frontier for almost 2 orders of magnitude"。

## 风险/局限
- 定价可持续性未被长期验证（可能补贴）；放弃字符串生成意味着不能用于聊天/写代码等需文本输出的任务。
- 工作流评测由团队内部构建，可能存在偏差。

## 核心线索
- GitHub：https://github.com/typesafe-ai/system-one-adapter-python
- 首发来源：https://typesafe.ai/blog/introducing-system-one-models-and-jev
- 发布时间：2026-09-16
- 当前状态：早期（early access）