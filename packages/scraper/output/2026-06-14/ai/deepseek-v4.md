# DeepSeek-V4

## 技术定义 (What)
DeepSeek 第四代大模型，采用 CSA（压缩稀疏注意力）和 HCA（重度压缩注意力）混合架构，支持 100 万 token 上下文。专为 Agent 工作流设计，在长上下文推理中实现 10% FLOPs 和 7% KV Cache 的极致优化。

## 行业痛点 (Why)
现有长上下文模型在 Agent 场景下存在三大问题：1）KV Cache 随上下文长度线性增长，GPU 显存快速耗尽；2）长任务中每轮工具调用都要重新计算注意力，推理成本高；3）多轮对话中推理链被截断，Agent 丢失状态。

## 旧范式 vs 新范式
- **旧做法**：使用标准 Transformer 注意力机制，上下文窗口扩展到 100K+ token 时，KV Cache 占用数 GB 甚至数十 GB 显存，推理延迟和成本大幅上升。Agent 难以在长任务中保持连贯推理。
- **新做法**：混合注意力架构：CSA 层通过 4x 压缩 + top-k 稀疏选择处理长序列，HCA 层通过 128x 压缩进行稠密注意力。KV Cache 仅需传统架构的 2%，FLOPs 降低 90%。保留跨用户轮次的推理链，支持累积式思考。

## 生产力影响 (How)
使百万 token 上下文 Agent 应用成为可能。相同硬件上可支持更长上下文或更高并发，推理成本大幅降低。跨轮次推理保留让多步骤 Agent 任务更连贯，减少状态重建开销。

## 采用成本
开源模型可直接从 Hugging Face 下载，支持 vLLM 等推理框架。需要理解 CSA/HCA 架构特性以优化部署。适用于需要处理超长文档、长对话历史的 Agent 场景。

## 核心线索
- GitHub：https://huggingface.co/blog/deepseekv4
- 来源：https://huggingface.co/blog/deepseekv4
- 发布时间：2026-06-14
