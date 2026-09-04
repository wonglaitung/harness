# Slotstream — MoE Expert Slot Streaming

## 技术定义 (What)
Slotstream 是一个 Swift 编写的本地推理引擎，用"专家槽位流式加载"（Expert Slot Streaming）技术，将 125B 参数的 MoE 模型（105GB/4-bit）运行在 48GB Mac 上。核心思路：保持 3.8GB 的 trunk 常驻内存，其余 101+GB 的专家权重根据推理需要从 SSD 按槽位流式加载，使用 MLX/Metal 统一内存架构，无需 Python。兼容 Ollama 和 OpenAI chat API。

## 行业痛点 (Why)
MoE 大模型（如 Qwen3.8-Flash-Next 的 125B 参数）在消费级硬件上无法运行——标准 loader 在一个 token 之前就吃满 48GB swap。现有方案（llama.cpp offloading）也有同样问题。根本瓶颈不是算力，而是内存管理策略。

## 旧范式 vs 新范式
- **旧做法**：全量模型加载：将模型全部权重加载到内存（或 naive swap），MoE 的 101GB 专家权重直接压垮消费级机器。即便 GGUF 量化后，125B MoE 对 48GB 统一内存依然不可行。
- **新做法**：Expert Slot Streaming：将 MoE 的专家权重池化为一组固定槽位（slots），每次推理只加载激活的少数专家到槽位中，实现 105GB 磁盘 → 32GB 内存的运行时。配合 Trunk 常驻（attention 层仅 3.8GB）、auto-sizing 内存策略、sweep 批处理（256 token 批量 stream 专家权重），达到 warm decode ~12 tok/s。首次提出"SlotStreaming"作为 MoE 消费级推理的系统性方案。

## 生产力影响 (How)
让开发者用 48GB MacBook 就能本地运行 125B MoE 模型，无需云端 GPU。对 Agent 开发者尤其有价值：本地模型推理零成本、零延迟、完全隐私。兼容 Ollama/OpenAI API，现有工具无需修改。Slotted expert loading 概念可推广到所有 MoE 模型的消费级部署。

## 采用成本
免费开源（MIT），需要 Apple Silicon + 110GB 磁盘空间 + macOS 14+。通过 curl 一行安装。学习成本极低（即装即用）。

## 核心线索
- GitHub：https://github.com/carloslfu/slotstream
- 来源：https://news.ycombinator.com/item?id=49524447
- 发布时间：2026-09-05
