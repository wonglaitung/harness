# MoE Expert Streaming — 跨层共享 Slot Pool + 磁盘专家层（experts_offload）

## 技术定义 (What)
在 Transformers 中新增 experts_offload 路径：专家权重按需从 SSD 流式载入，设备侧只保留一个有界 LRU 缓存。关键创新是把这个缓存实现为 slot pool——一块所有层共享的预分配设备张量 + 每层一份"专家 id → slot"映射表。由于 router 的专家 id 被重映射为 slot 编号，这个池在算子看来就是一张普通 expert bank，于是原生 grouped_mm 可直接在其上运行，无需自写专家 matmul。配合量化专家缓存（如 q3）与 Metal 8-bit，实现 180B 级 MoE 在 32GB 统一内存机器上运行。

## 行业痛点 (Why)
现有三条卸载路线都有硬伤：llama.cpp 把专家留在 CPU 上"就地算"，专家放得进 RAM 就很好，放不进则 page cache 抖动；vLLM 的 --cpu-offload 只做 pinned RAM 直读、无缓存无磁盘层，热点专家每 token 都要再过一次 PCIe；Transformers+Accelerate 以"模块"为单位卸载，MoE 的一整层专家库每 token 全量搬一次只为用其中 8-10 个，实测 0.16 tok/s。

## 旧范式 vs 新范式
- **旧做法**：专家放不进显存时，要么全量搬权重（Accelerate、vLLM 默认），要么改在 CPU 上算（llama.cpp --cpu-moe），要么退回逐专家的 Python 循环（把 grouped_mm 的融合优势丢掉）。
- **新做法**：只流式搬运 router 实际选中的专家，经一个有界缓存落地，且缓存以"槽位池"形式伪装成常规专家库，从而在享受流式卸载的同时保住融合算子。实测：A10G 上 Qwen3.6-35B-A3B 达 82-88 tok/s（llama.cpp --fit on 为 63-64，vLLM 最优配置 20.1，Accelerate 0.16）；OLMoE 上 34.6 vs 原生 38.1 tok/s，即卸载后仅损失约 9%。

## 生产力影响 (How)
把"跑不动的大 MoE"变成"慢一点但能跑"：单卡 24GB 或 32GB 笔记本可承载 180B 级 MoE。且这是向上游 Transformers 提的 PR（#50717），一旦合并，所有依赖 from_pretrained 的项目自动获得该能力，而非停留在某个独立引擎里。

## 采用成本
中低。API 表现为 device_map={"": "mps", "experts.*": "disk"} + experts_offload={cache_bytes, quantized_experts} 两个参数。当前需从 PR 分支安装；需预先产出量化专家文件；SSD 成为瓶颈，缓存预算需实测调优。

## 核心线索
- GitHub：https://github.com/huggingface/transformers/pull/50717
- 来源：https://huggingface.co/blog/moe-expert-streaming
- 发布时间：2026-11-19
