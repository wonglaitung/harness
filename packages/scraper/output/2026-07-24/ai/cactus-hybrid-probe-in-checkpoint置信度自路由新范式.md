# Cactus Hybrid

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 首次在模型checkpoint内嵌入置信度探针(probe)，输出结构化confidence而非从文本解析 |
| 采用广度 | ☆☆☆/5 | 支持Cactus/MLX/Transformers/llama.cpp四引擎，Gemma 4 E2B首发模型 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026年7月首发，极新 |
| 社区热度 | ☆☆☆/5 | Show HN 183 points，GitHub早期 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)
Cactus Hybrid是一种后训练方法，在模型checkpoint内部嵌入一个轻量级"探针"(probe)，该探针读取模型隐藏状态(hidden state)并输出0-1之间的结构化置信度分数。这不是从生成文本中解析不确定度，而是模型级别的校准信号。

## 行业痛点 (Why)
小型端侧模型(如Gemma 4 E2B)速度快、隐私好，但经常出错。现有方案用token entropy（词元熵）判断不确定度，AUROC仅0.549，几乎随机。开发者无法可靠地知道何时该信任小模型、何时该路由到大模型。

## 旧范式 vs 新范式
- **旧做法**：用token entropy或logprob估计不确定度（AUROC~0.55），从生成文本解析置信度，需要大模型处理所有请求
- **新做法**：checkpoint内嵌probe直接输出结构化confidence（AUROC 0.814），低置信度自动路由到大模型，仅15-55%请求需要大模型

## 生产力影响 (How)
- 端侧模型处理45-85%的请求，大幅降低API成本
- 跨模态通用：probe在零音频训练数据下，音频AUROC仍达0.79-0.88，证明读取的是模态无关的正确性信号
- 一行代码实现路由：`if confidence < 0.85: answer = ask_a_bigger_model(prompt)`

## 采用成本
- 低成本：直接使用预训练Hybrid模型，无需额外训练probe
- 支持Cactus Python / MLX / Transformers / llama.cpp四种推理引擎
- 需要配合大模型API作为回退路由

## 采用案例
- Gemma 4 E2B Hybrid：2B端侧模型匹配Gemini 3.1 Flash-Lite性能，仅路由15-55%请求
- 量化兼容：4-bit量化下路由比例略增但仍有效（25-50%），3-bit下仍可用

## 风险/局限
- MMLU-Pro在4-bit量化下路由比例升至~90%，接近全部回退
- llama.cpp需要编译patch，非原生支持
- 当前仅支持Gemma 4 E2B，尚未验证更大模型的probe效果
- probe读取hidden state，device_map="auto"等加速策略会导致crash

## 核心线索
- GitHub：https://github.com/cactus-compute/cactus-hybrid
- HuggingFace：https://huggingface.co/collections/Cactus-Compute/cactus-hybrid-6a60da4551074db058e8bb64
- 首发来源：Show HN (183 points)
- 发布时间：2026年7月
- 当前状态：活跃 / 早期