# Ollaya / Typed Decision Models (System One / Jev-class)

## 技术定义 (What)
决策模型（decision model）读取 state（消息/邮件/ticket/任意 JSON）+ 类型化问题（choice/score/yes-no），在单次前向传播中返回带校准概率的答案，从不逐 token 生成文本。Ollaya 是这套模型的本地运行时：像 Ollama 跑 LLM 一样，用 `ollaya run laya` 拉取并服务决策模型，且与 TypeSafe 的 `/v1/systemone` 线格式完全兼容。

## 行业痛点 (Why)
传统 LLM 做分类/路由/守护（guardrail）决策需要逐 token 生成，慢（数百 ms）、贵、且输出非结构化、概率未校准。而需要「判断」而非「生成」的 Agent 场景（是否放行某条命令、退款意图、风险等级）被大模型的热度掩盖了更优解。

## 旧范式 vs 新范式
- **旧做法**：用通用 LLM 逐 token 生成"yes/no/invoice"等分类结果，延迟 200ms+、token 计费、概率不可靠。
- **新做法**：用专用决策模型单次前向读取 option-letter logits 或 marker span，8–190ms 返回结构化、校准过的概率答案；可通过 Modelfile 烘焙自定义问题集；通过 MCP 直接服务给 Claude/Cursor 等 Agent。

## 生产力影响 (How)
Agent 的「大脑」与「反射弧」分离：判断类路径从数百 ms 降到个位数 ms、成本降 1–2 个数量级。为 Agent 的 guardrail、路由、triage 提供可本地部署、可审查、可校准的确定性组件，是 Agent 走向生产可靠性的关键基础设施。

## 采用成本
极低。一条命令安装单一二进制，TypeSafe SDK 改一个环境变量即用；模型权重来自作者原仓库（sha256 校验），3MB ONNX 图。CPU 可跑，NVIDIA GPU 可达毫秒级。

## 核心线索
- GitHub：https://github.com/ollaya-dev/ollaya
- 来源：https://ollaya.dev/（HN 311 points）
- 发布时间：2026-09-26
