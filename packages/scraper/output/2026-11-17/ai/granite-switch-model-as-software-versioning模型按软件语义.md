# Granite Switch — Model-as-Software Versioning（模型按软件语义版本化）+ Adapter-Composed Model

## 技术定义 (What)
把一个语言模型拆成「冻结底座 + 一组可组合的 cache-efficient aLoRA 适配器」，每个适配器是一个专门能力（闲聊 / 通用决策 / 安全决策 / 语音转写 / 领域分类）。关键创新在于两点：(1) 所有适配器共享底座的 KV cache，因此叠加 N 个专家能力的显存占用≈底座本身，实现「一个 endpoint 多种模态与决策流」；(2) 模型开始像软件一样发布——4.1.1 是 patch release，"意思和软件里一样：完全向后兼容 4.1、无需迁移、底层增量改进"。这是模型从「整体重训的制品」变成「可打补丁、可语义版本化的运行时组件」。

## 行业痛点 (Why)
今天的模型部署现实是：每加一种能力（结构化决策、安全审核、语音）就要多部署一个模型、多占一份 GPU。企业为了「一个客服系统同时要聊天 + 判断退款是否合规 + 转写通话」不得不同时挂三个模型，成本与运维复杂度线性增长。与此同时，模型升级是一门「大版本赌博」——换模型等于换掉全部行为，回归风险高到让企业常年不敢升级，只能冻结在老版本上吃技术债。缺少的是既有能力组合能力、又有安全升级路径的模型发布机制。

## 旧范式 vs 新范式
- **旧做法**：一个模型 = 一个整体权重制品。加能力 = 训一个新模型或外挂另一个服务；升级模型 = 换掉整个权重，宁可冻结旧版也不敢升。能力之间无法共享 KV cache，每多一项能力就多一份显存成本。
- **新做法**：模型 = 冻结底座 + 语义版本化的适配器集合。能力以 aLoRA 形式增量叠加、共享 KV cache（8B 底座装 4 个适配器仍只占约一份底座显存）；升级是 patch level 的、向后兼容的、无需迁移的模型「补丁」。用户也可以自行从 Granite Libraries 组合出自定义 Switch 模型。

## 生产力影响 (How)
直接降低两类成本：显存/GPU 数量（多能力单 endpoint）与升级回归风险（patch 级升级）。IBM 的对照实测里，Granite-Switch-4.1-30B（冻结底座 + 4 个专用 aLoRA）跑完一个真实的 5 步 RAG 工作流，显著快于 Jev-27B（冻结底座 + 1 个通用决策 LoRA）；自建 3B Switch 模型在 Doom 中做到 60–100 decisions/秒（对比 Jev 报告的 10 次/秒），且能同时对话。对开发者意味着：可以在同一条 `v1/systemone` API 路径上混用决策与闲聊调用，并复用 shared prefix cache。

## 采用成本
中低。使用「batteries included」的 4.1-8B/30B 只需在 vLLM 加插件，`llama.cpp` 与下游平台已原生支持，开箱即用；自定义组合则需理解 adapter catalog 与 granitelib 生态，Adapter SDK（Mellea）尚在「计划发布」阶段，社区自造适配器的工具链还不成熟。学习曲线主要花在「换掉『模型是黑盒制品』的心智模型」上。

## 核心线索
- GitHub：https://github.com/generative-computing/granite-switch
- 来源：https://huggingface.co/blog/ibm-granite/granite-switch-4-1-1
- 发布时间：2026-11-17
