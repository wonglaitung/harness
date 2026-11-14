# Decision Models（决策模型）— State + Questions → Decisions + Probabilities

## 技术定义 (What)
决策模型（Decision Model）是一类不做文本生成、只做概率判定的模型。它接收「状态 (state)」和一组预先定义的可选答案 (primitives)，直接返回结构化决策 + 每个选项的概率分布，完全不生成 text token。接口为：State + Questions + Allowed Answers → Decisions + Probabilities。它区别于传统分类器（类别烘焙在分类头里，加一个类要重训）和零样本分类（用 NLI 做蕴含判断），定位在两者之间。Hugging Face 已将其收编为 transformers 的一等 pipeline 任务 `pipeline("decision")`。

## 行业痛点 (Why)
大量生产任务（工单路由、紧急度判定、意图识别、是否退款）本质是"在有限选项里选一个"，却被塞给自回归 LLM 去生成 JSON。这带来三重浪费：① schema 无保证——模型可能吐非法 JSON、多出字段、或给出不在候选集里的答案；② 约束解码（Outlines/XGrammar）虽能强制结构，但引入额外计算开销与工程复杂度；③ 生成整段回复本身就为开放式生成设计，对选择题是无谓计算。

## 旧范式 vs 新范式
- **旧做法**：让 LLM 生成 JSON → 祈祷 schema 合规 → 不合法就加重试 / 上约束解码 → 分类任务用固定标签分类头，新增一个标签就要重新收集数据并重训模型
- **新做法**：输入 state + 声明式 questions（含 type 与每个候选的 criteria）→ 模型直接输出概率分布，零文本生成 → 选项在推理时给定，随时增删无需重训 → 自带 confidence，天然可做阈值降级与人工兜底 → 一行 `pipeline("decision")` 接入 transformers 生态

## 生产力影响 (How)
① 延迟与成本：分类/路由类调用从"逐 token 生成"变成"一次前向概率"，token 成本降到接近 0；② 工程简化：不再需要 JSON 解析容错、约束解码、重试循环；③ 可运维性：返回 confidence 使"低置信→转人工"成为一等公民，而不是事后补丁；④ 业务敏捷：新增一个部门/标签只改 prompt 里的 primitives，不需要重训，这是相对传统分类器的结构性优势。

## 采用成本
低。已是 Hugging Face transformers 官方 pipeline 任务，示例中模型 `autotrust/GEV-26B-Decide` 一行调用即可；无需自建推理栈。主要成本是思维切换：识别出"哪些调用其实不需要生成文本"。

## 核心线索
- GitHub：https://huggingface.co/blog/decision
- 来源：https://huggingface.co/blog/decision
- 发布时间：2026-11-14
