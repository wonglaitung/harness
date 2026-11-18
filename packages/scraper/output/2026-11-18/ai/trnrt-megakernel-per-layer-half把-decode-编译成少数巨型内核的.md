# TrnRT — Megakernel-per-Layer-Half：把 decode 编译成少数巨型内核的 Trainium2 推理范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆/5 | 「按层半融合 megakernel」+「编译缓存即分发产物」是明确的架构主张，不是版本升级。作者给出了判据：decode 受限的不是带宽而是内核边界与暴露的 collective，因此必须把 collective 移进 kernel |
| 采用广度 | ☆☆/5 | 目前仅 RunAnywhere 自家 + SemiAnalysis AgentX 发布；无外部项目集成证据 |
| 时间新鲜 | ☆☆☆☆☆/5 | 2026-11-04 博客 + 仓库同期，约两周 |
| 社区热度 | ⚠️☆☆/5 | Show HN 仅 46 points，未达 50 门槛；靠 benchmark 数字而非讨论热度支撑 |
| **总体判断** | ⚠️ | **观察中——技术主张清晰且有硬数据，但生态尚未形成** |

## 技术定义（What）

TrnRT 是 RunAnywhere 开源的 LLM 推理引擎（Apache-2.0），专为 AWS Trainium2 编写。核心做法是把 decode 阶段按「每半个网络层一个 NKI 内核」整体融合（KDA attention、fused DSA 层、mHC、MoE FFN 各成一个 kernel），并把所有计算图在 CPU 主机上离线编译成缓存，服务机只加载、不编译。单台 trn2.48xlarge（16 芯片）跑两个 tensor-parallel=32 的引擎，前置 session-affine 路由器 + FP8 KV 分页 radix 树前缀缓存（含 host 内存二级）。当前支持 GLM-5.3-Flash（320B MoE / 18B active / FP8 / 1M 上下文）。

## 行业痛点（Why）

Trainium 生态长期缺一个「能跑大 MoE + 1M 上下文 + 高并发 agent 会话」的开源服务栈；官方 Neuron 路径需要每台机器现场编译，启动以小时计；而 decode 在 Trainium 上不是被内存带宽限制，而是被小指令、内核边界和暴露的 collective 主导——传统逐算子内核天然低效。

## 旧范式 vs 新范式

- **旧做法**：逐算子（per-op）图执行 + 服务机现场编译 + GPU 优先的推理栈；容量规划以「每 GPU 每小时多少钱」为单位
- **新做法**：按「层半」融合的 megakernel + 编译产物即分发物（offline compile cache）；容量规划改用「每 TB-加速器内存每小时」

## 生产力影响（How）

SemiAnalysis AgentX 真实 agent 流量下，单框 32 并发 agent、batch 12：28.9 req/min、3.57M tokens/min，spot 价 $0.040/M tokens。100 万 token 冷提示首 token 190.8s（对比此前的 Kiln v0.2.0 同半框 1651.7s，快 8.7×），命中缓存后追问首 token 1.84s。

## 采用成本

高。需 trn2.48xlarge 服务机 + x86_64 编译主机；编译缓存构建耗时数小时；仅支持单一模型家族，新增模型需实现全套内核。

## 风险/局限

- **单模型绑定**：只有 GLM-5.3-Flash 可用，模型换代即需重做编译与内核
- **无 GPU 基线对照**：作者明确承认尚未在相同 trace 上跑 P5 对比，省钱的结论缺一半证据
- **精度牺牲**：稀疏注意力提示处理中保留了一处近似，影响 1.2% 的 selection
- **公开仓库与测速构建不完全一致**：作者自述 benchmark 用的是内部构建
- **未做任务级准确率评估**

## 核心线索

- GitHub：https://github.com/RunanywhereAI/trnrt
- 技术博客：https://runanywhere.ai/blog/glm-5-3-flash-trainium2-nki-megakernels
- 发布时间：2026-11-04
- 当前状态：活跃（Apache-2.0，单模型可用）
