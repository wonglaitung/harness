# Mistral Large 4 (Le Chonk) — 开放权重即防御能力（Reproduce-then-Patch 作为可验证奖励）

## 技术定义 (What)
Mistral Large 4（代号 Le Chonk）是 1T 总参 / 49B 激活的多模态 MoE 开放权重模型，1M 上下文。技术上叠加两种稀疏：MoE 路由（128 专家选 4 + 1 共享专家）负责选前馈网络，DeepSeek Sparse Attention (DSA) indexer 负责选最多 2048 个 key 位置；注意力用 MLA 压缩 KV，3:1 RoPE/NoPE 交替并跨层共享 KV 状态。它的真正主张不在架构，而在"网络安全能力必须开放权重"：在 Artificial Analysis Cyber Index 上得 82%，而多个闭源前沿模型因拒答而接近 0 分。原因是"修复漏洞首先需要复现漏洞"，而漏洞复现与事件响应在输入侧看起来就像攻击，闭源过滤器会直接阻断——防御方在最需要能力的时刻失去能力。此外 reproduce-then-patch 任务天然带可验证奖励，可直接构成 RL 环境来训练更小的安全模型。

## 行业痛点 (Why)
安全防御工作（漏洞复现、恶意软件分析、检测规则编写、事件响应）在闭源模型的拒答过滤器下会被系统性误伤：防御方输入看起来像攻击方输入，于是拿到的是拒答而不是能力。同时 API 依赖意味着在真实事件中可能被切断访问，使用政策也不在自己手里。这是一条被"安全对齐"反向惩罚的正当工作流。

## 旧范式 vs 新范式
- **旧做法**：安全能力被默认收拢在闭源前沿模型内部，以"不提供攻击能力"为名把复现类请求一律拒答；防御方只能用拒答率高的模型做安全运营，或者用未对齐的越狱模型冒险。安全能力的可得性由供应商的 usage policy 单向决定。
- **新做法**：把「复现→补丁」这条闭环作为开放权重模型的第一等能力发布，并把它的可验证性（补丁能否通过验证）当作训练信号：既可以直接 fine-tune / RL 出更小的专用安全模型，也可以让研究者直接测量模型的拒答行为而不是相信供应商的描述。能力归属从"供应商政策"转移到"部署方控制"——使用政策与部署位置都在用户手上。

## 生产力影响 (How)
安全团队可以在自有代码库、崩溃日志、恶意软件样本上构建闭环系统，而不必担心请求被拒或被审计切断。82% 的 Cyber Index 与"闭源近 0"的对比，直接给出一条选型依据：需要复现能力的场景，开放权重是唯一可行路径。同时该模型在 JailbreakBench / StrongREJECT / AgentHarm 上的平均拒答率高于任何其他开放权重模型，说明"放开复现"不等于"放开有害请求"——这个分离本身是可复用的对齐结论。

## 采用成本
模型级成本：1T 总参的 MoE，实际部署需较大显存/多卡或重量化；官方提供 FP8 与 NVFP4 两种变体，并有 Unsloth 与 llama.cpp 团队产出的 GGUF，本地路径已通。生态接入成本低：Transformers、vLLM、llama.cpp、TRL 微调、Inference Endpoints、Dell Enterprise Hub 均已就绪。许可为 Mistral Ecosystem Open-Weight License（MIT 衍生，对 model-as-a-service 有额外限制），商用需读条款。

## 核心线索
- GitHub：https://huggingface.co/mistralai/Mistral-Large-4-1T-A52B
- 来源：https://huggingface.co/blog/mistral-large4
- 发布时间：2026-11-18
