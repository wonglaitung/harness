# NeoMME

## 技术定义 (What)
NeoMME 是一个从零训练的多模态编码器家族（260M/800M），用单一双向 Transformer 同时处理文本 token 和原始图像 patch，不依赖预训练视觉塔或因果语言模型。使用 masked discrete-diffusion 目标训练，微调后可用于视觉文档检索。

## 行业痛点 (Why)
现有视觉文档检索系统依赖"预训练视觉编码器→投影器→因果语言模型"三件套架构，参数量大、推理慢。视觉编码器和语言模型各自预训练，导致跨模态对齐困难且计算冗余——检索任务根本不需要因果解码器的自回归生成能力。

## 旧范式 vs 新范式
- **旧做法**：ColPali/ColModernVBERT 式架构：SigLIP2 视觉塔 → MLP 投影 → ModernBERT 文本编码器，两个独立预训练模型拼接，参数冗余，推理吞吐受限。
- **新做法**：NeoMME：单一双向 Transformer，文本和图像 patch 走同一计算路径，从零训练。动态分辨率保持宽高比，交替滑窗+全局注意力层。260M 模型在 L40S 上编码 51 页/秒，是 ColModernVBERT 的 2 倍，且用层级 token 池化和非对称量化将索引存储从 1.5MB/页压缩到 6kB（255×）。

## 生产力影响 (How)
为视觉文档 RAG 提供更高效的基础设施：更小模型、更快推理、更小索引。单一 Transformer 架构也更易于训练、微调和部署。Apache 2.0 开源。

## 采用成本
已在 HuggingFace Transformers 中可用，有 demo 空间可直接体验。训练需从零开始（524B tokens），但推理即插即用。

## 核心线索
- GitHub：https://huggingface.co/collections/Hcompany/neomme
- 来源：https://huggingface.co/blog/Hcompany/neomme
- 发布时间：2026-09-05
