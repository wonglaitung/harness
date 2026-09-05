# NeoMME：单一 Transformer 多模态编码器新范式

## 新范式评分

| 维度 | 评分 | 证据 |
|------|------|------|
| 概念创新 | ☆☆☆☆☆/5 | 首次将文本和图像统一到单一双向 Transformer，无预训练视觉塔和语言模型 |
| 采用广度 | ☆☆/5 | 刚发布，采用待观察；但架构创新度高 |
| 时间新鲜 | ☆☆☆☆☆/5 | 发布于 2026-09-03（arXiv: 2609.01657） |
| 社区热度 | ☆☆☆/5 | HuggingFace 官方博客，Apache 2.0 开源 |
| **总体判断** | ✅ | **新范式** |

## 技术定义 (What)

NeoMME 是一个从零开始训练的多语言多模态编码器家族（260M 和 800M 参数）。**单一双向 Transformer 同时处理文本 token 和原始图像 patch**，使用 masked discrete-diffusion 目标训练。不像传统 VLM 需要独立的 SigLIP/SigLIP2 视觉塔 + 投影器 + 因果语言模型，NeoMME 在同一个编码器中统一处理两种模态。

## 行业痛点 (Why)

当前视觉文档检索的主流架构依赖生成式 VLM（如 ColPali），必须携带预训练视觉塔和因果解码器的参数和计算开销。但这些任务（检索、分类、标注）并不需要自回归生成文本，因果解码器是多余的负担。

## 旧范式 vs 新范式

- **旧做法**：ColPali 类方法 = SigLIP2 视觉塔 → 投影器 → 因果语言模型（如 PaliGemma），参数量大，推理慢
- **新做法**：NeoMME = 图像 patch + 文本 token → 单一双向 Transformer 编码器 → 稠密 + 晚期交互 embedding

## 生产力影响 (How)

- **吞吐量**：260M 模型在 L40S 上达到约 **51 页/秒**，约为 ColModernVBERT 的 **2 倍**
- **索引存储**：通过分层 token pooling + 非对称量化，晚期交互索引从 ~1.5 MB/页压缩至 **6 kB/页（255 倍缩小）**，保留 95%+ nDCG@10
- **架构简化**：不需要维护和调优两个独立模型（视觉塔 + 文本模型）

## 采用成本

- **时间**：HuggingFace Transformers 原生支持，可直接加载
- **学习曲线**：与传统 VLM 不同，需理解 masked diffusion 预训练
- **硬件**：260M 可在 L40S 上运行，门槛低

## 采用案例

- **NeoMME-Retriever**：基于 ColPali 页面图像方法微调，单次前向返回稠密 + 晚期交互 embedding，位列 ViDoRe v3 Pareto 前沿
- 适用于：视觉文档检索、多模态分类、OCR-free 文档理解

## 风险/局限

- 260M/800M 参数量相对较小，复杂多模态推理能力待验证
- 多语言覆盖度（131k BPE tokenizer）在实际使用中的表现待社区反馈
- 生态尚未建立，与 ColPali 生态的兼容性有限

## 核心线索

- HuggingFace 集合：[Hcompany/neomme](https://hf.co/collections/Hcompany/neomme)
- 论文：[arXiv 2609.01657](https://arxiv.org/abs/2609.01657)
- 许可证：Apache 2.0
- 发布时间：2026-09-03
- 当前状态：活跃开发中